from agents.case_store import SQLiteCaseStore


def _case(case_id="CASE-00001", accounts=("A", "B")):
    return {
        "case_id": case_id,
        "pattern": "circular_flow",
        "accounts": list(accounts),
        "risk_score": 90,
        "risk_tier": "High",
        "evidence": "A -> B -> A",
    }


def test_record_and_read_back(tmp_path):
    store = SQLiteCaseStore(str(tmp_path / "cases.db"))
    store.record_run([_case()], run_id="run-1")
    cases = store.all_cases()
    assert len(cases) == 1
    assert cases[0]["case_id"] == "CASE-00001"
    assert cases[0]["accounts"] == ["A", "B"]
    assert cases[0]["times_seen"] == 1


def test_same_run_id_does_not_inflate_count(tmp_path):
    store = SQLiteCaseStore(str(tmp_path / "cases.db"))
    store.record_run([_case()], run_id="run-1")
    store.record_run([_case()], run_id="run-1")
    assert store.all_cases()[0]["times_seen"] == 1


def test_new_run_id_increments_count(tmp_path):
    store = SQLiteCaseStore(str(tmp_path / "cases.db"))
    enriched_first = store.record_run([_case()], run_id="run-1")
    store.record_run([_case()], run_id="run-2")
    case = store.all_cases()[0]
    assert case["times_seen"] == 2
    # first_seen is preserved from the first sighting.
    assert case["first_seen"] == enriched_first[0]["first_seen"]


def test_reset_clears_store(tmp_path):
    store = SQLiteCaseStore(str(tmp_path / "cases.db"))
    store.record_run([_case()], run_id="run-1")
    store.reset()
    assert store.all_cases() == []
