# Fraud Ring Triage Copilot

Track 02 — Fraud Watch

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

Install dependencies:

pip install -r requirements.txt

Run the app:

python -m streamlit run app.py

Then upload:

data/sample_transactions.csv

## Project Structure

fraud-watch/
├── app.py
├── requirements.txt
├── README.md
├── product_brief.pdf
├── data/
│   └── sample_transactions.csv
├── agents/
│   ├── pattern_finder.py
│   ├── risk_ranker.py
│   ├── action_recommender.py
│   ├── report_writer.py
│   └── memory.py
└── reports/

## Demo Flow

1. Upload the sample transaction CSV.
2. Review suspicious patterns found by Pattern Finder.
3. Inspect risk scores from Risk Ranker.
4. Review recommended analyst actions.
5. Download a generated fraud case report.
6. Open Agent Trace / Shared Memory to inspect the multi-agent handoff.

## Status

MVP complete. Future improvements include direct Cognee integration, richer graph visualization, larger Kaggle dataset support, and automated case clustering.
