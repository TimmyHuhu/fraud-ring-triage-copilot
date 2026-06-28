import pandas as pd

from agents.pattern_finder import (
    infer_columns,
    find_circular_flows,
    find_repeated_low_value_transfers,
    find_track02_account_ring,
    run_pattern_finder,
)


def test_infer_columns_matches_common_names():
    df = pd.DataFrame(
        {"Sender": [], "Receiver": [], "Amount": [], "Timestamp": []}
    )
    cols = infer_columns(df)
    assert cols["sender"] == "Sender"
    assert cols["receiver"] == "Receiver"
    assert cols["amount"] == "Amount"
    assert cols["timestamp"] == "Timestamp"


def test_infer_columns_returns_none_when_missing():
    df = pd.DataFrame({"foo": [], "bar": []})
    cols = infer_columns(df)
    assert cols["sender"] is None
    assert cols["amount"] is None


def test_find_circular_flows_detects_and_normalizes_rotation():
    df = pd.DataFrame(
        {
            "sender": ["B", "C", "A"],
            "receiver": ["C", "A", "B"],
            "amount": [100, 100, 100],
        }
    )
    findings = find_circular_flows(df, "sender", "receiver", "amount")
    assert len(findings) == 1
    finding = findings[0]
    assert finding["pattern"] == "circular_flow"
    # Cycle is rotated to start at the smallest node regardless of input order.
    assert finding["accounts"][0] == "A"
    assert finding["evidence"] == "A → B → C → A"


def test_find_circular_flows_coerces_non_numeric_amounts():
    df = pd.DataFrame(
        {
            "sender": ["A", "B"],
            "receiver": ["B", "A"],
            "amount": ["100", "not-a-number"],
        }
    )
    # Should not raise even though one amount is unparseable.
    findings = find_circular_flows(df, "sender", "receiver", "amount")
    assert len(findings) == 1


def test_find_repeated_low_value_transfers():
    df = pd.DataFrame(
        {
            "sender": ["X", "X", "X", "X", "P", "Q"],
            "receiver": ["Y", "Y", "Y", "Y", "R", "S"],
            "amount": [10, 10, 10, 10, 1000, 2000],
        }
    )
    findings = find_repeated_low_value_transfers(df, "sender", "receiver", "amount")
    assert len(findings) == 1
    assert findings[0]["pattern"] == "repeated_low_value_transfers"
    assert findings[0]["num_transactions"] == 4
    assert findings[0]["accounts"] == ["X", "Y"]


def test_find_track02_account_ring():
    df = pd.DataFrame(
        {
            "sender": ["AC-1"] * 10,
            "receiver": ["AC-2"] * 10,
            "amount": [600] * 10,
        }
    )
    findings = find_track02_account_ring(df, "sender", "receiver", "amount")
    assert len(findings) == 1
    finding = findings[0]
    assert finding["pattern"] == "track02_account_counterparty_ring"
    assert finding["num_transactions"] == 10
    assert finding["total_amount"] == 6000


def test_run_pattern_finder_reports_missing_columns():
    df = pd.DataFrame({"foo": [1], "bar": [2]})
    result = run_pattern_finder(df)
    assert result["status"] == "missing_columns"
    assert result["findings"] == []
