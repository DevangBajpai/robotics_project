# Robotics App POC

A proof-of-concept Streamlit dashboard for monitoring a robotics fleet.

## Files
- `app.py` — Streamlit app (robot fleet status, task log, battery levels)
- `requirements.txt` — Python dependencies

## Run Locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Databricks Deployment
1. Push this repo to GitHub
2. In Databricks, create a new App and point it to this repo
3. Set the entry point to `app.py`
