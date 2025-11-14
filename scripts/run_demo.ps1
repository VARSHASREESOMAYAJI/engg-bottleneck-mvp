#!/usr/bin/env bash
python -m uvicorn app:app --host 127.0.0.1 --port 9000 & PID=$!
sleep 1
echo "Metrics:"
curl -s http://127.0.0.1:9000/metrics | jq
echo "Anomalies:"
curl -s http://127.0.0.1:9000/anomalies | jq
kill $PID
