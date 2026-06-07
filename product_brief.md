# Fraud Ring Triage Copilot

## Track
Track 02 - Fraud Watch

## End User
Fraud analysts who have only three minutes to decide whether a suspicious case should be escalated.

## Problem
Fraud rings can evade traditional rule-based systems by using low-value transfers, circular fund flows, and coordinated accounts.

## Product
A multi-agent investigation dashboard that detects hidden fraud patterns, ranks suspicious cases, recommends analyst actions, and generates downloadable case reports.

## Agents
1. Pattern Finder - detects suspicious transaction patterns.
2. Risk Ranker - scores and prioritizes cases.
3. Action Recommender - recommends escalation, watchlist, or dismissal.
4. Analyst Report Writer - generates a downloadable investigation report.

## Tools Used
- Cognee for shared agent memory
- Geodo for domain research
- Trupeer for demo recording
- Kaggle Track 02 dataset
- Streamlit, pandas, NetworkX, scikit-learn

## Success Criteria
A judge can load the dashboard, inspect the top suspicious cases, understand why each case is risky, and download a case report without reading raw transaction data.