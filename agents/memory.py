from datetime import datetime
from pathlib import Path
import json


TRACE_PATH = Path("reports/latest_agent_trace.json")


def make_trace_event(
    agent_name: str,
    action: str,
    input_summary: str,
    output_summary: str,
    metadata: dict | None = None,
) -> dict:
    return {
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "agent_name": agent_name,
        "action": action,
        "input_summary": input_summary,
        "output_summary": output_summary,
        "metadata": metadata or {},
    }


def save_trace(events: list[dict]) -> None:
    TRACE_PATH.parent.mkdir(exist_ok=True)
    TRACE_PATH.write_text(
        json.dumps(events, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def load_trace() -> list[dict]:
    if not TRACE_PATH.exists():
        return []

    return json.loads(TRACE_PATH.read_text(encoding="utf-8"))
