from agents.risk_ranker import make_case_id, score_finding, run_risk_ranker


def test_make_case_id_is_deterministic():
    finding = {"pattern": "circular_flow", "accounts": ["A", "B", "C"]}
    assert make_case_id(finding) == make_case_id(finding)
    assert make_case_id(finding).startswith("CASE-")


def test_make_case_id_ignores_account_order():
    a = {"pattern": "circular_flow", "accounts": ["A", "B", "C"]}
    b = {"pattern": "circular_flow", "accounts": ["C", "A", "B"]}
    assert make_case_id(a) == make_case_id(b)


def test_make_case_id_differs_by_pattern():
    a = {"pattern": "circular_flow", "accounts": ["A", "B"]}
    b = {"pattern": "repeated_low_value_transfers", "accounts": ["A", "B"]}
    assert make_case_id(a) != make_case_id(b)


def test_score_track02_ring_is_high_tier():
    finding = {
        "pattern": "track02_account_counterparty_ring",
        "accounts": ["AC-1", "AC-2"],
        "total_amount": 6000,
        "num_transactions": 10,
    }
    case = score_finding(finding)
    assert case["risk_tier"] == "High"
    assert case["risk_score"] >= 85


def test_score_is_capped_at_100():
    finding = {
        "pattern": "track02_account_counterparty_ring",
        "accounts": ["AC-1", "AC-2"],
        "total_amount": 10_000_000,
        "num_transactions": 1000,
    }
    case = score_finding(finding)
    assert case["risk_score"] == 100


def test_run_risk_ranker_sorts_by_score_descending():
    findings = [
        {"pattern": "repeated_low_value_transfers", "accounts": ["A", "B"]},
        {
            "pattern": "track02_account_counterparty_ring",
            "accounts": ["AC-1", "AC-2"],
            "total_amount": 6000,
            "num_transactions": 10,
        },
    ]
    result = run_risk_ranker(findings)
    scores = [c["risk_score"] for c in result["cases"]]
    assert scores == sorted(scores, reverse=True)
    assert result["num_cases"] == 2
