# Fraud Ring Triage Copilot

Track 02 — Fraud Watch

[![CI](https://github.com/TimmyHuhu/fraud-ring-triage-copilot/actions/workflows/ci.yml/badge.svg)](https://github.com/TimmyHuhu/fraud-ring-triage-copilot/actions/workflows/ci.yml)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![Streamlit](https://img.shields.io/badge/Built%20with-Streamlit-FF4B4B.svg)

Fraud Ring Triage Copilot is a multi-agent investigation dashboard that helps fraud analysts detect hidden fraud rings, rank suspicious cases, recommend next actions, and generate downloadable case reports.

## Problem

Fraud rings often avoid traditional rule-based systems by using low-value transfers, circular fund flows, and coordinated accounts. Fraud analysts need to decide quickly which cases deserve escalation.

## Solution

This project provides a Streamlit dashboard that turns raw transaction data into analyst-ready fraud cases.

The system runs a four-agent workflow:

1. Pattern Finder detects suspicious transaction structures such as circular fund flows and repeated low-value transfers.
2. Risk Ranker assigns each finding a risk score and risk tier.
3. Action Recommender recommends escalation, manual review, watchlist, or dismissal.
4. Analyst Report Writer generates a downloadable fraud case report.

## Screenshots

> Add screenshots or a short GIF of the dashboard here to show the workflow at a
> glance. Suggested shots: the upload + metrics view, the ranked cases table, and
> a generated case report.
>
> ```markdown
> ![Dashboard overview](docs/screenshot-dashboard.png)
> ![Ranked cases](docs/screenshot-cases.png)
> ```

## Cognee-Ready Shared Memory

The dashboard includes an Agent Trace / Shared Memory section.

In this MVP, agent handoffs are stored as a local JSON trace. This simulates the shared memory layer that can later be backed by Cognee.

In production, Cognee can persist investigation context across sessions, allowing agents to remember previous findings, risk scores, recommendations, and reports.

## Demo Dataset

A sample dataset is included:

data/sample_transactions.csv

It contains examples of circular fund flows, repeated low-value transfers, and normal transactions.

## Product Brief

See the full product brief:

product_brief.pdf

## Tech Stack

- Python
- Streamlit
- pandas
- NetworkX
- scikit-learn
- Cognee-ready memory layer
- GitHub

## Run Locally

Requires Python 3.10 or newer.

Create and activate a virtual environment, then install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate        # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

(Optional) Configure environment variables for the planned Cognee integration.
The app runs fully offline on the sample data without this step:

```bash
cp .env.example .env             # then edit .env with your own values
```

Run the app:

```bash
python -m streamlit run app.py
```

Then upload the sample dataset:

```text
data/sample_transactions.csv
```

## Development

Install the development dependencies and run the test suite:

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest
```

The agent logic is covered by unit tests under `tests/`, and
[GitHub Actions](.github/workflows/ci.yml) runs them on Python 3.10–3.12 for
every push and pull request. See [CONTRIBUTING.md](CONTRIBUTING.md) for the full
contribution workflow.

## Project Structure

```text
fraud-ring-triage-copilot/
├── app.py
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
├── README.md
├── CONTRIBUTING.md
├── LICENSE
├── .env.example
├── product_brief.pdf
├── data/
│   └── sample_transactions.csv
├── agents/
│   ├── __init__.py
│   ├── pattern_finder.py
│   ├── risk_ranker.py
│   ├── action_recommender.py
│   ├── report_writer.py
│   └── memory.py
├── tests/
│   ├── test_pattern_finder.py
│   ├── test_risk_ranker.py
│   ├── test_action_recommender.py
│   ├── test_report_writer.py
│   └── test_memory.py
├── .github/
│   ├── workflows/ci.yml
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
└── reports/
```

## Demo Flow

1. Upload the sample transaction CSV.
2. Review suspicious patterns found by Pattern Finder.
3. Inspect risk scores from Risk Ranker.
4. Review recommended analyst actions.
5. Download a generated fraud case report.
6. Open Agent Trace / Shared Memory to inspect the multi-agent handoff.

## Status

MVP complete. Future improvements include direct Cognee integration, richer graph visualization, larger Kaggle dataset support, and automated case clustering.

## License

Released under the [MIT License](LICENSE). Copyright (c) 2026 Timmy Hu.
