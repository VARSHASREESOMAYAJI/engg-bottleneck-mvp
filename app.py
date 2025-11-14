# app.py
from fastapi import FastAPI, Query
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
from pydantic import BaseModel
from sklearn.ensemble import IsolationForest

app = FastAPI(title="Engg Bottleneck MVP")

# Load sample data on startup
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

commits = pd.DataFrame(load_json("data/sample/commits.json"))
deploys = pd.DataFrame(load_json("data/sample/deploys.json"))

# normalize timestamps
for df in (commits, deploys):
    if not df.empty:
        df["ts"] = pd.to_datetime(df["ts"])

# --- Metric computations ---
def deployment_frequency(repo=None, window_days=30):
    d = deploys.copy()
    if repo:
        d = d[d["repo"] == repo]
    cutoff = d["ts"].max() - pd.Timedelta(days=window_days)
    recent = d[d["ts"] >= cutoff]
    # deployments per week (approx)
    weeks = max(window_days / 7.0, 1.0)
    freq = len(recent) / weeks
    return {"deployment_frequency_per_week": round(freq, 3), "count_window": len(recent)}

def lead_time_for_changes(repo=None, window_days=30):
    # naive approach: match commits to next deploy in same repo
    c = commits.copy()
    d = deploys.copy()
    if repo:
        c = c[c["repo"] == repo]
        d = d[d["repo"] == repo]
    if c.empty or d.empty:
        return {"lead_time_hours_avg": None}
    lead_times = []
    for _, commit in c.iterrows():
        later_deploys = d[d["ts"] >= commit["ts"]]
        if not later_deploys.empty:
            first = later_deploys.iloc[0]
            lead = (first["ts"] - commit["ts"]).total_seconds() / 3600.0
            lead_times.append(lead)
    if not lead_times:
        return {"lead_time_hours_avg": None}
    arr = np.array(lead_times)
    return {"lead_time_hours_avg": round(arr.mean(), 2), "samples": len(arr)}

def change_failure_rate(repo=None, window_days=30):
    d = deploys.copy()
    if repo:
        d = d[d["repo"] == repo]
    cutoff = d["ts"].max() - pd.Timedelta(days=window_days) if not d.empty else pd.Timestamp.now()
    window = d[d["ts"] >= cutoff]
    if window.empty:
        return {"change_failure_rate": None}
    failures = window[window["success"] == False]
    rate = len(failures) / max(1, len(window))
    return {"change_failure_rate": round(rate, 3), "deploy_count": len(window), "failures": len(failures)}

def time_to_restore(repo=None, window_days=90):
    d = deploys.sort_values("ts").copy()
    if repo:
        d = d[d["repo"] == repo]
    # naive: for each failed deploy, time until next successful deploy
    if d.empty:
        return {"time_to_restore_hours_avg": None}
    ttrs = []
    for idx, row in d.iterrows():
        if row["success"] == False:
            later = d[d["ts"] > row["ts"]]
            success = later[later["success"] == True]
            if not success.empty:
                delta = (success.iloc[0]["ts"] - row["ts"]).total_seconds() / 3600.0
                ttrs.append(delta)
    if not ttrs:
        return {"time_to_restore_hours_avg": None}
    return {"time_to_restore_hours_avg": round(np.mean(ttrs), 2), "samples": len(ttrs)}

# --- Anomaly detection: rolling z-score on lead_time samples ---
def compute_lead_time_series(repo=None, days=90):
    # build daily average lead time by finding commits and mapping to next deploy
    c = commits.copy()
    d = deploys.copy()
    if repo:
        c = c[c["repo"] == repo]; d = d[d["repo"] == repo]
    if c.empty or d.empty:
        return pd.Series(dtype=float)
    records = []
    for _, commit in c.iterrows():
        later = d[d["ts"] >= commit["ts"]]
        if not later.empty:
            lt = (later.iloc[0]["ts"] - commit["ts"]).total_seconds() / 3600.0
            records.append({"date": commit["ts"].date(), "lead": lt})
    if not records:
        return pd.Series(dtype=float)
    df = pd.DataFrame(records).groupby("date").lead.mean().sort_index()
    # reindex last `days`
    idx = pd.date_range(end=df.index.max(), periods=min(days, 90))
    df = df.reindex(idx.date, fill_value=np.nan)
    s = pd.Series(df.values.flatten(), index=idx)
    s = s.interpolate().fillna(method="bfill")
    return s

def detect_anomalies_zscore(series, z_thresh=2.5):
    if series.empty:
        return []
    mu = series.mean()
    sigma = series.std(ddof=0) if series.std(ddof=0) > 0 else 1.0
    z = (series - mu) / sigma
    anomalous = z[abs(z) > z_thresh]
    return [{"date": str(idx.date()), "value": float(series.loc[idx]), "z": float(z.loc[idx])} for idx in anomalous.index]

@app.get("/metrics")
def get_metrics(repo: str = Query(None)):
    out = {}
    out["deployment_frequency"] = deployment_frequency(repo)
    out["lead_time_for_changes"] = lead_time_for_changes(repo)
    out["change_failure_rate"] = change_failure_rate(repo)
    out["time_to_restore"] = time_to_restore(repo)
    return out

@app.get("/anomalies")
def get_anomalies(repo: str = Query(None)):
    s = compute_lead_time_series(repo)
    anomalies = detect_anomalies_zscore(s)
    # also run a very small IsolationForest if series long enough
    iso_list = []
    if len(s.dropna()) >= 10:
        X = s.fillna(s.mean()).values.reshape(-1,1)
        iso = IsolationForest(contamination=0.05, random_state=42)
        preds = iso.fit_predict(X)
        for i, p in enumerate(preds):
            if p == -1:
                iso_list.append({"date": str(s.index[i].date()), "value": float(s.iloc[i])})
    return {"zscore_anomalies": anomalies, "isolation_forest": iso_list}

@app.get("/")
def root():
    return {"service": "Engg Bottleneck MVP", "endpoints": ["/metrics", "/anomalies", "/docs"]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=9000)
