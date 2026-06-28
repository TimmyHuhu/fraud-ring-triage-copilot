from pathlib import Path

from agents import memory
from agents.memory import make_trace_event, save_trace, load_trace


def test_make_trace_event_structure():
    event = make_trace_event(
        agent_name="Pattern Finder",
        action="Detect patterns",
        input_summary="3 transactions",
        output_summary="1 finding",
        metadata={"status": "success"},
    )
    assert event["agent_name"] == "Pattern Finder"
    assert event["metadata"] == {"status": "success"}
    assert event["timestamp"].endswith("UTC")


def test_save_and_load_trace_round_trip(tmp_path, monkeypatch):
    trace_file = tmp_path / "trace.json"
    monkeypatch.setattr(memory, "TRACE_PATH", trace_file)

    events = [make_trace_event("A", "act", "in", "out")]
    save_trace(events)

    assert Path(trace_file).exists()
    loaded = load_trace()
    assert loaded == events


def test_load_trace_returns_empty_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(memory, "TRACE_PATH", tmp_path / "does_not_exist.json")
    assert load_trace() == []
