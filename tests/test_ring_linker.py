from agents.ring_linker import jaccard, cluster_cases


def test_jaccard_basic():
    assert jaccard({"a", "b"}, {"a", "b"}) == 1.0
    assert jaccard({"a", "b"}, {"c", "d"}) == 0.0
    assert jaccard({"a", "b", "c"}, {"b", "c"}) == 2 / 3
    assert jaccard(set(), set()) == 0.0


def _case(case_id, accounts, pattern="circular_flow", risk=80):
    return {
        "case_id": case_id,
        "accounts": list(accounts),
        "pattern": pattern,
        "risk_score": risk,
    }


def test_overlapping_cases_cluster_together():
    cases = [
        _case("C1", ["A", "B", "C"]),
        _case("C2", ["B", "C"], pattern="repeated_low_value_transfers", risk=60),
        _case("C3", ["X", "Y"]),
    ]
    clusters = cluster_cases(cases, threshold=0.5)
    by_size = {c["size"]: c for c in clusters}
    assert by_size[2]["case_ids"] == ["C1", "C2"]
    assert by_size[2]["accounts"] == ["A", "B", "C"]
    assert by_size[2]["max_risk_score"] == 80
    assert by_size[1]["case_ids"] == ["C3"]


def test_threshold_controls_linking():
    cases = [
        _case("C1", ["A", "B", "C", "D"]),
        _case("C2", ["C", "D", "E", "F"]),  # Jaccard = 2/6 ~= 0.33
    ]
    assert len(cluster_cases(cases, threshold=0.5)) == 2
    assert len(cluster_cases(cases, threshold=0.3)) == 1


def test_cluster_id_is_deterministic():
    cases = [_case("C1", ["A", "B"]), _case("C2", ["A", "B"])]
    first = cluster_cases(cases, threshold=0.5)[0]["cluster_id"]
    second = cluster_cases(cases, threshold=0.5)[0]["cluster_id"]
    assert first == second
    assert first.startswith("RING-")
