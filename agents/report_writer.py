from datetime import datetime


def build_case_report(case: dict) -> str:
    accounts = case.get("accounts", [])
    reasons = case.get("reasons", [])
    source_finding = case.get("source_finding", {})

    report = f"""# Fraud Case Report

## Case Overview

Case ID: {case.get("case_id", "N/A")}
Generated At: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}
Risk Score: {case.get("risk_score", "N/A")}
Risk Tier: {case.get("risk_tier", "N/A")}
Priority: {case.get("priority", "N/A")}
Recommended Action: {case.get("recommended_action", "N/A")}

## Suspicious Pattern

Pattern Type: {case.get("pattern", "N/A")}

Evidence:
{case.get("evidence", "No evidence provided.")}

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

{source_finding}

## Recommended Analyst Next Step

1. Review the transaction trail.
2. Check whether the involved accounts share device, IP, address, or payment instrument identifiers.
3. Compare this behavior against recent historical activity.
4. Decide whether to escalate, watchlist, or dismiss the case.

## Analyst Notes

Add notes here during manual review.
"""

    return report


def run_report_writer(recommendations: list[dict]) -> dict:
    reports = []

    for case in recommendations:
        report_markdown = build_case_report(case)

        reports.append({
            "case_id": case.get("case_id", "N/A"),
            "risk_score": case.get("risk_score", 0),
            "risk_tier": case.get("risk_tier", "N/A"),
            "recommended_action": case.get("recommended_action", "N/A"),
            "report_filename": f"{case.get('case_id', 'case')}_fraud_report.md",
            "report_markdown": report_markdown,
        })

    return {
        "status": "success",
        "num_reports": len(reports),
        "reports": reports,
    }
