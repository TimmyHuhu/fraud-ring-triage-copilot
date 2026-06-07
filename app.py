import streamlit as st
import pandas as pd
from agents.pattern_finder import run_pattern_finder
from agents.risk_ranker import run_risk_ranker

st.set_page_config(
    page_title="Fraud Ring Triage Copilot",
    page_icon="🕵️",
    layout="wide",
)

st.title("Fraud Ring Triage Copilot")
st.caption("Track 02 — Fraud Watch")

st.markdown(
    """
    A multi-agent dashboard for detecting hidden fraud rings, ranking suspicious
    cases, recommending analyst actions, and generating downloadable reports.
    """
)

st.divider()

col1, col2, col3, col4 = st.columns(4)

col1.metric("Transactions", "—")
col2.metric("Accounts", "—")
col3.metric("Suspicious Cases", "—")
col4.metric("High Risk Cases", "—")

st.subheader("Upload Transaction Dataset")

uploaded_file = st.file_uploader(
    "Upload a CSV file with transaction data",
    type=["csv"],
)

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    st.success("Dataset loaded successfully.")
    st.write("Preview:")
    st.dataframe(df.head(20), use_container_width=True)

    st.subheader("Dataset Summary")
    st.write(df.describe(include="all"))

    st.subheader("Agent 1: Pattern Finder")

    result = run_pattern_finder(df)

    if result["status"] == "success":
        st.success(f"Pattern Finder completed. Found {result['num_findings']} suspicious patterns.")

        st.write("Inferred columns:")
        st.json(result["columns"])

        if result["findings"]:
            findings_df = pd.DataFrame(result["findings"])
            st.dataframe(findings_df, use_container_width=True)

            st.subheader("Agent 2: Risk Ranker")

            ranked_result = run_risk_ranker(result["findings"])

            st.success(f"Risk Ranker completed. Ranked {ranked_result['num_cases']} suspicious cases.")

            cases_df = pd.DataFrame([
                {
                    "case_id": case["case_id"],
                    "risk_score": case["risk_score"],
                    "risk_tier": case["risk_tier"],
                    "pattern": case["pattern"],
                    "accounts": ", ".join(case["accounts"]),
                    "evidence": case["evidence"],
                    "reasons": " | ".join(case["reasons"]),
                }
                for case in ranked_result["cases"]
            ])

            st.dataframe(cases_df, use_container_width=True)
        else:
            st.info("No suspicious patterns found with the current rules.")
    else:
        st.warning(result["message"])
        st.write("Inferred columns:")
        st.json(result["columns"])
else:
    st.info("Upload a CSV file to begin analysis.")

st.divider()

st.subheader("Agent Workflow")

st.markdown(
    """
    1. **Pattern Finder** — detects circular flows, low-value repeated transfers, and coordinated accounts.
    2. **Risk Ranker** — scores and prioritizes suspicious cases.
    3. **Action Recommender** — recommends escalation, review, watchlist, or dismissal.
    4. **Analyst Report Writer** — generates a downloadable investigation report.
    """
)
