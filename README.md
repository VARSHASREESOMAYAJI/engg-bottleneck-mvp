README.md

# Engineering Bottleneck Detector — MVP

Lightweight DORA metrics engine + anomaly detector.  
Processes sample Git commit & deployment timelines and produces:

- Deployment Frequency  
- Lead Time for Changes  
- Change Failure Rate  
- Time to Restore  
- Lead Time Anomaly Detection (Z-Score + IsolationForest)  

This is a fast, local, demo-ready MVP.

---

## 🚀 Quick Start

**1. Create virtual environment**
```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt


2. Start the API

python -m uvicorn app:app --host 127.0.0.1 --port 9000


3. Call metrics (new terminal)

.\.venv\Scripts\Activate.ps1
Invoke-RestMethod -Uri http://127.0.0.1:9000/metrics -Method Get | ConvertTo-Json


Anomalies

Invoke-RestMethod -Uri http://127.0.0.1:9000/anomalies -Method Get | ConvertTo-Json


Interactive Docs
http://127.0.0.1:9000/docs

📂 Sample Data Included

Inside data/sample/:

commits.json

deploys.json

These drive all DORA + anomaly outputs.

📌 Scope of This MVP

FastAPI backend

Synthetic Git + Deploy timelines

Daily DORA metrics

Lead Time anomaly detection

One-command local demo

🔮 Upgrade Paths (for full version)

Add Jira issue transitions

Add TimescaleDB for timeseries

Add Prophet for forecasting

Add React dashboard (cockpit + anomalies)

📄 License

MIT License.

