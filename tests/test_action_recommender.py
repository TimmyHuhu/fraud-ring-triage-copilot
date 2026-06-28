import pytest

from agents.action_recommender import recommend_action, run_action_recommender


@pytest.mark.parametrize(
    "score,expected_action,expected_priority",
    [
        (90, "Escalate immediately", "P1"),
        (75, "Manual review", "P2"),
        (55, "Add to watchlist", "P3"),
        (20, "No immediate action", "P4"),
    ],
)
def test_recommend_action_by_score(score, expected_action, expected_priority):
    case = {"risk_score": score, "pattern": "circular_flow"}
    result = recommend_action(case)
    assert result["recommended_action"] == expected_action
    assert result["priority"] == expected_priority


def test_recommend_action_preserves_case_fields():
    case = {"risk_score": 90, "pattern": "circular_flow", "case_id": "CASE-00001"}
    result = recommend_action(case)
    assert result["case_id"] == "CASE-00001"
    assert "action_rationale" in result


def test_run_action_recommender_counts():
    cases = [
        {"risk_score": 90, "pattern": "circular_flow"},
        {"risk_score": 20, "pattern": "repeated_low_value_transfers"},
    ]
    result = run_action_recommender(cases)
    assert result["num_recommendations"] == 2
