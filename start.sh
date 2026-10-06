#!/usr/bin/env bash
set -e

echo "Starting The SilentZone Sentinel Services..."
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 &
sleep 2
python -m streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true --server.runOnSave false
