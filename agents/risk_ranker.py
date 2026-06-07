def score_finding(finding: dict) -> dict:
    pattern = finding.get("pattern", "")
    score = 0
    reasons = []

    if pattern == "track02_account_counterparty_ring":
        score += 85
        reasons.append("Coordinated account-to-account transfer ring detected.")

        total_amount = finding.get("total_amount", 0)
        if total_amount >= 100000:
            score += 10
            reasons.append(f"Total ring exposure is {total_amount}.")

        num_transactions = finding.get("num_transactions", 0)
        if num_transactions >= 100:
            score += 5
            reasons.append(f"{num_transactions} coordinated transfers detected.")

    elif pattern == "circular_flow":
        score += 70
        reasons.append("Circular fund flow detected.")

        num_accounts = finding.get("num_accounts", 0)
        if num_accounts >= 3:
            score += 15
            reasons.append(f"{num_accounts} accounts are involved in the loop.")

        total_amount = finding.get("total_amount", 0)
        if total_amount >= 1000:
            score += 10
            reasons.append(f"Total loop amount is {total_amount}.")

    elif pattern == "repeated_low_value_transfers":
        score += 55
        reasons.append("Repeated low-value transfers detected.")

        num_transactions = finding.get("num_transactions", 0)
        if num_transactions >= 3:
            score += min(num_transactions * 5, 25)
            reasons.append(f"{num_transactions} repeated transfers between the same accounts.")

        avg_amount = finding.get("avg_amount", 0)
        if avg_amount < 100:
            score += 10
            reasons.append(f"Average transaction amount is low: {avg_amount}.")

    else:
        score += 30
        reasons.append("Unclassified suspicious pattern detected.")

    score = min(score, 100)

    if score >= 85:
        tier = "High"
    elif score >= 65:
        tier = "Medium"
    else:
        tier = "Low"

    return {
        "case_id": f"CASE-{abs(hash(str(finding))) % 100000:05d}",
        "risk_score": score,
        "risk_tier": tier,
        "pattern": pattern,
        "accounts": finding.get("accounts", []),
        "evidence": finding.get("evidence", ""),
        "reasons": reasons,
        "source_finding": finding,
    }


def run_risk_ranker(findings: list[dict]) -> dict:
    cases = [score_finding(finding) for finding in findings]
    cases = sorted(cases, key=lambda x: x["risk_score"], reverse=True)

    return {
        "status": "success",
        "num_cases": len(cases),
        "cases": cases,
    }
