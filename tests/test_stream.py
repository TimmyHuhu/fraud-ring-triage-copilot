import pandas as pd
import pytest

from agents.stream import compute_run_id, iter_batches


def test_compute_run_id_is_stable_and_distinct():
    assert compute_run_id(b"abc") == compute_run_id(b"abc")
    assert compute_run_id(b"abc") != compute_run_id(b"abd")


def _df(n):
    return pd.DataFrame(
        {
            "sender": [f"A{i}" for i in range(n)],
            "receiver": [f"B{i}" for i in range(n)],
            "amount": list(range(n)),
            "timestamp": pd.date_range("2026-06-01", periods=n, freq="h").astype(str),
        }
    )


def test_iter_batches_splits_and_preserves_rows():
    df = _df(10)
    batches = iter_batches(df, "timestamp", 5)
    assert len(batches) == 5
    assert sum(len(b) for b in batches) == 10


def test_iter_batches_is_time_ordered():
    df = _df(6).iloc[::-1].reset_index(drop=True)  # reverse chronological
    batches = iter_batches(df, "timestamp", 3)
    first_ts = batches[0]["timestamp"].iloc[0]
    last_ts = batches[-1]["timestamp"].iloc[-1]
    assert first_ts < last_ts


def test_iter_batches_rejects_bad_count():
    with pytest.raises(ValueError):
        iter_batches(_df(3), "timestamp", 0)
