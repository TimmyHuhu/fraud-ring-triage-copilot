import streamlit as st
import pandas as pd

from agents.pattern_finder import run_pattern_finder
from agents.risk_ranker import run_risk_ranker
from agents.action_recommender import run_action_recommender
from agents.report_writer import run_report_writer
from agents.memory import make_trace_event, save_trace


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

st.subheader("Upload Transaction Dataset")

uploaded_file = st.file_uploader(
    "Upload a CSV file with transaction data",
    type=["csv"],
)

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    trace_events = []

    result = run_pattern_finder(df)

    trace_events.append(
        make_trace_event(
            agent_name="Pattern Finder",
            action="Detect suspicious transaction patterns",
            input_summary=f"Received {len(df)} transactions.",
            output_summary=f"Found {result.get('num_findings', 0)} suspicious patterns.",
            metadata={
                "status": result.get("status"),
                "inferred_columns": result.get("columns"),
            },
        )
    )

    suspicious_cases_count = 0
    high_risk_cases_count = 0
    accounts_count = 0

    if result["status"] == "success":
        ranked_result = run_risk_ranker(result["findings"])

        high_risk_cases_count = sum(
            1 for case in ranked_result["cases"] if case["risk_tier"] == "High"
        )

        trace_events.append(
            make_trace_event(
                agent_name="Risk Ranker",
                action="Score and rank suspicious cases",
                input_summary=f"Received {len(result['findings'])} suspicious findings.",
                output_summary=(
                    f"Ranked {ranked_result['num_cases']} cases; "
                    f"{high_risk_cases_count} high-risk cases found."
                ),
                metadata={
                    "num_cases": ranked_result["num_cases"],
                    "high_risk_cases": high_risk_cases_count,
                },
            )
        )

        action_result = run_action_recommender(ranked_result["cases"])

        action_counts = {}
        for case in action_result["recommendations"]:
            action = case["recommended_action"]
            action_counts[action] = action_counts.get(action, 0) + 1

        trace_events.append(
            make_trace_event(
                agent_name="Action Recommender",
                action="Recommend analyst next actions",
                input_summary=f"Received {ranked_result['num_cases']} ranked cases.",
                output_summary=(
                    f"Generated {action_result['num_recommendations']} recommendations."
                ),
                metadata={
                    "action_counts": action_counts,
                },
            )
        )

        report_result = run_report_writer(action_result["recommendations"])

        trace_events.append(
            make_trace_event(
                agent_name="Analyst Report Writer",
                action="Generate downloadable case reports",
                input_summary=(
                    f"Received {action_result['num_recommendations']} recommended actions."
                ),
                output_summary=(
                    f"Generated {report_result['num_reports']} analyst-ready reports."
                ),
                metadata={
                    "num_reports": report_result["num_reports"],
                },
            )
        )

        save_trace(trace_events)

        suspicious_cases_count = ranked_result["num_cases"]

        sender_col = result["columns"].get("sender")
        receiver_col = result["columns"].get("receiver")

        if sender_col and receiver_col:
            accounts = set(df[sender_col].astype(str)) | set(df[receiver_col].astype(str))
            accounts_count = len(accounts)
    else:
        ranked_result = None
        action_result = None
        report_result = None
        save_trace(trace_events)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Transactions", len(df))
    col2.metric("Accounts", accounts_count if accounts_count else "—")
    col3.metric("Suspicious Cases", suspicious_cases_count)
    col4.metric("High Risk Cases", high_risk_cases_count)

    st.success("Dataset loaded successfully.")

    st.subheader("Preview")
    st.dataframe(df.head(20).astype(str), use_container_width=True)

    st.subheader("Dataset Summary")
    st.write(df.describe(include="all"))

    st.subheader("Agent 1: Pattern Finder")

    if result["status"] == "success":
        st.success(
            f"Pattern Finder completed. Found {result['num_findings']} suspicious patterns."
        )

        st.write("Inferred columns:")
        st.json(result["columns"])

        if result["findings"]:
            findings_df = pd.DataFrame(result["findings"])
            st.dataframe(findings_df.astype(str), use_container_width=True)

            st.subheader("Agent 2: Risk Ranker")

            st.success(
                f"Risk Ranker completed. Ranked {ranked_result['num_cases']} suspicious cases."
            )

            cases_df = pd.DataFrame([
                {
                    "case_id": case["case_id"],
                    "risk_score": case["risk_score"],
                    "risk_tier": case["risk_tier"],
                    "pattern": case["pattern"],
                    "accounts": ", ".join(map(str, case["accounts"])),
                    "evidence": case["evidence"],
                    "reasons": " | ".join(case["reasons"]),
                }
                for case in ranked_result["cases"]
            ])

            st.dataframe(cases_df.astype(str), use_container_width=True)

            st.subheader("Agent 3: Action Recommender")

            st.success(
                f"Action Recommender completed. Generated {action_result['num_recommendations']} recommendations."
            )

            recommendations_df = pd.DataFrame([
                {
                    "case_id": case["case_id"],
                    "risk_score": case["risk_score"],
                    "risk_tier": case["risk_tier"],
                    "priority": case["priority"],
                    "recommended_action": case["recommended_action"],
                    "pattern": case["pattern"],
                    "evidence": case["evidence"],
                    "action_rationale": case["action_rationale"],
                }
                for case in action_result["recommendations"]
            ])

            st.dataframe(recommendations_df.astype(str), use_container_width=True)

            st.subheader("Agent 4: Analyst Report Writer")

            st.success(
                f"Report Writer completed. Generated {report_result['num_reports']} downloadable reports."
            )

            report_options = {
                f"{report['case_id']} — Risk {report['risk_score']} — {report['recommended_action']}": report
                for report in report_result["reports"]
            }

            selected_report_label = st.selectbox(
                "Select a case report to preview and download",
                list(report_options.keys()),
            )

            selected_report = report_options[selected_report_label]

            st.markdown(selected_report["report_markdown"])

            st.download_button(
                label="Download Analyst Report",
                data=selected_report["report_markdown"],
                file_name=selected_report["report_filename"],
                mime="text/markdown",
            )

            st.subheader("Agent Trace / Shared Memory")

            st.caption(
                "This local trace simulates the shared memory layer that can later be backed by Cognee."
            )

            trace_df = pd.DataFrame(trace_events)

            st.dataframe(
                trace_df[["timestamp", "agent_name", "action", "input_summary", "output_summary"]],
                use_container_width=True,
            )

            with st.expander("View raw memory JSON"):
                st.json(trace_events)

        else:
            st.info("No suspicious patterns found with the current rules.")
    else:
        st.warning(result["message"])
        st.write("Inferred columns:")
        st.json(result["columns"])

else:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Transactions", "—")
    col2.metric("Accounts", "—")
    col3.metric("Suspicious Cases", "—")
    col4.metric("High Risk Cases", "—")

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
