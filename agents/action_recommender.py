def recommend_action(case: dict) -> dict:
    score = case.get("risk_score", 0)
    pattern = case.get("pattern", "")

    if score >= 85:
        action = "Escalate immediately"
        priority = "P1"
        rationale = "High-risk case with strong fraud indicators. Analyst should review immediately."
    elif score >= 70:
        action = "Manual review"
        priority = "P2"
        rationale = "Moderate-to-high risk case. Requires analyst validation before escalation."
    elif score >= 50:
        action = "Add to watchlist"
        priority = "P3"
        rationale = "Suspicious behavior detected, but evidence is not strong enough for escalation."
    else:
        action = "No immediate action"
        priority = "P4"
        rationale = "Low-risk case based on current evidence."

    if pattern == "circular_flow" and score >= 85:
        rationale += " Circular fund flow suggests possible coordinated movement of funds."
    elif pattern == "repeated_low_value_transfers":
        rationale += " Repeated low-value transfers may indicate threshold avoidance."

    return {
        **case,
        "recommended_action": action,
        "priority": priority,
        "action_rationale": rationale,
    }


def run_action_recommender(cases: list[dict]) -> dict:
    recommendations = [recommend_action(case) for case in cases]

    return {
        "status": "success",
        "num_recommendations": len(recommendations),
        "recommendations": recommendations,
    }
