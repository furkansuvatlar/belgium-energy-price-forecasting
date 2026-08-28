# Belgium Day-Ahead Energy Price Forecasting Pipeline

An end-to-end MLOps and Data Engineering pipeline that autonomously fetches daily electricity market data from the ENTSO-E API, transforms features using dbt in Google BigQuery, predicts day-ahead prices via an Optuna-tuned XGBoost model, and delivers daily metrics to Looker Studio and Slack.

---

## System Architecture
```
[ENTSO-E API] ──(Python Ingestion)──> [Google BigQuery Raw]
│
(dbt Transformations)
│
▼
[Slack Alerts] <──(GitHub Actions)─── [XGBoost + Optuna]
│                                     │
└─────────────────────────────> [Looker Studio Dashboard]
```
---

## Live Dashboard & Performance Monitoring

<img width="1217" height="913" alt="Ekran görüntüsü 2026-08-28 152533" src="https://github.com/user-attachments/assets/11c307b6-f46f-4c45-950b-11cab949a88a" />



🔗 **Live Report:** [View Interactive Looker Studio Dashboard](https://datastudio.google.com/u/0/reporting/4df8d091-e8d0-4fdb-a047-227f663efcb6/page/6ht6F)

## Tech Stack & Key Features

* **Data Ingestion:** Automated Python scripts fetching price, load, and weather generation data from the ENTSO-E transparency platform.
* **Data Transformation (dbt & BigQuery):** In-warehouse feature engineering generating dynamic 24h/168h lags, rolling averages, and cyclical time features ($sin/cos$).
* **Machine Learning:** XGBoost Regression model optimized with **Optuna** hyperparameter tuning to minimize Mean Absolute Error (MAE).
* **CI/CD & MLOps:** Scheduled via **GitHub Actions** (CRON) to run autonomously every morning at 04:00 UTC.
* **Monitoring & Reporting:** Integrated **Slack Webhooks** for automated daily health checks and an interactive **Looker Studio Dashboard** tracking real-time MAE performance.

---

## Real-World Performance & Concept Drift

The pipeline handles live market volatility in real time. During abrupt market shifts (e.g., weekend demand drops or renewable generation spikes), the automated monitoring setup tracks Model Drift live via Looker Studio as the feature pipeline continually updates lag variables for self-correction.

---
