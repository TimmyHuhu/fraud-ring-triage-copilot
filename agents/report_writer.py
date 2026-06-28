from datetime import datetime, timezone
import html
import json


def build_case_report(case: dict) -> str:
    accounts = case.get("accounts", [])
    reasons = case.get("reasons", [])
    source_finding = case.get("source_finding", {})

    source_finding_text = json.dumps(
        source_finding,
        indent=2,
        ensure_ascii=False,
    )

    report = f"""# Fraud Case Report

## Case Overview

- **Case ID:** {case.get("case_id", "N/A")}
- **Generated At:** {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}
- **Risk Score:** {case.get("risk_score", "N/A")}
- **Risk Tier:** {case.get("risk_tier", "N/A")}
- **Priority:** {case.get("priority", "N/A")}
- **Recommended Action:** {case.get("recommended_action", "N/A")}

## Suspicious Pattern

- **Pattern Type:** {case.get("pattern", "N/A")}
- **Evidence:** {case.get("evidence", "No evidence provided.")}

## Accounts Involved

{", ".join(map(str, accounts)) if accounts else "No accounts listed."}

## Why This Case Is Risky

"""

    if reasons:
        for reason in reasons:
            report += f"- {reason}\n"
    else:
        report += "- No detailed reasons available.\n"

    report += f"""

## Action Rationale

{case.get("action_rationale", "No rationale provided.")}

## Source Finding

{source_finding_text}

## Recommended Analyst Next Step

1. Review the transaction trail.
2. Check whether the involved accounts share device, IP, address, or payment instrument identifiers.
3. Compare this behavior against recent historical activity.
4. Decide whether to escalate, watchlist, or dismiss the case.

## Analyst Notes

Add notes here during manual review.
"""

    return report


def build_case_report_html(case: dict) -> str:
    accounts = ", ".join(map(str, case.get("accounts", []))) or "No accounts listed."
    reasons = case.get("reasons", [])
    source_finding = json.dumps(
        case.get("source_finding", {}),
        indent=2,
        ensure_ascii=False,
    )

    reasons_html = "".join(
        f"<li>{html.escape(reason)}</li>" for reason in reasons
    ) or "<li>No detailed reasons available.</li>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Fraud Case Report - {html.escape(case.get("case_id", "N/A"))}</title>
  <style>
    body {{
      font-family: Arial, Helvetica, sans-serif;
      margin: 40px;
      line-height: 1.6;
      color: #1f2937;
      background: #f8fafc;
    }}
    .report {{
      max-width: 900px;
      margin: auto;
      background: white;
      padding: 32px;
      border-radius: 12px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
    }}
    h1 {{
      color: #111827;
      border-bottom: 3px solid #2563eb;
      padding-bottom: 12px;
    }}
    h2 {{
      color: #1f2937;
      margin-top: 28px;
      border-bottom: 1px solid #e5e7eb;
      padding-bottom: 6px;
    }}
    .badge {{
      display: inline-block;
      padding: 4px 10px;
      border-radius: 999px;
      font-weight: bold;
      background: #fee2e2;
      color: #991b1b;
    }}
    .summary-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin-top: 16px;
    }}
    .card {{
      background: #f3f4f6;
      padding: 14px;
      border-radius: 8px;
    }}
    pre {{
      background: #111827;
      color: #f9fafb;
      padding: 16px;
      border-radius: 8px;
      overflow-x: auto;
    }}
    .footer {{
      margin-top: 32px;
      font-size: 0.9em;
      color: #6b7280;
    }}
  </style>
</head>
<body>
  <div class="report">
    <h1>Fraud Case Report</h1>

    <h2>Case Overview</h2>
    <div class="summary-grid">
      <div class="card"><strong>Case ID:</strong> {html.escape(case.get("case_id", "N/A"))}</div>
      <div class="card"><strong>Generated At:</strong> {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}</div>
      <div class="card"><strong>Risk Score:</strong> {html.escape(str(case.get("risk_score", "N/A")))}</div>
      <div class="card"><strong>Risk Tier:</strong> <span class="badge">{html.escape(case.get("risk_tier", "N/A"))}</span></div>
      <div class="card"><strong>Priority:</strong> {html.escape(case.get("priority", "N/A"))}</div>
      <div class="card"><strong>Recommended Action:</strong> {html.escape(case.get("recommended_action", "N/A"))}</div>
    </div>

    <h2>Suspicious Pattern</h2>
    <p><strong>Pattern Type:</strong> {html.escape(case.get("pattern", "N/A"))}</p>
    <p><strong>Evidence:</strong> {html.escape(case.get("evidence", "No evidence provided."))}</p>

    <h2>Accounts Involved</h2>
    <p>{html.escape(accounts)}</p>

    <h2>Why This Case Is Risky</h2>
    <ul>
      {reasons_html}
    </ul>

    <h2>Action Rationale</h2>
    <p>{html.escape(case.get("action_rationale", "No rationale provided."))}</p>

    <h2>Source Finding</h2>
    <pre>{html.escape(source_finding)}</pre>

    <h2>Recommended Analyst Next Step</h2>
    <ol>
      <li>Review the transaction trail.</li>
      <li>Check whether the involved accounts share device, IP, address, or payment instrument identifiers.</li>
      <li>Compare this behavior against recent historical activity.</li>
      <li>Decide whether to escalate, watchlist, or dismiss the case.</li>
    </ol>

    <h2>Analyst Notes</h2>
    <p>Add notes here during manual review.</p>

    <div class="footer">
      Generated by Fraud Ring Triage Copilot.
    </div>
  </div>
</body>
</html>
"""


def run_report_writer(recommendations: list[dict]) -> dict:
    reports = []

    for case in recommendations:
        report_markdown = build_case_report(case)
        report_html = build_case_report_html(case)

        reports.append({
            "case_id": case.get("case_id", "N/A"),
            "risk_score": case.get("risk_score", 0),
            "risk_tier": case.get("risk_tier", "N/A"),
            "recommended_action": case.get("recommended_action", "N/A"),
            "report_filename": f"{case.get('case_id', 'case')}_fraud_report.html",
            "report_markdown": report_markdown,
            "report_html": report_html,
        })

    return {
        "status": "success",
        "num_reports": len(reports),
        "reports": reports,
    }
