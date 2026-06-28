import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


class CaseStore(Protocol):
    """Cross-run persistence of fraud cases.

    The Cognee integration described in the README would implement this same
    interface and replace SQLiteCaseStore without touching the app.
    """

    def record_run(self, cases: list[dict], run_id: str) -> list[dict]: ...

    def all_cases(self) -> list[dict]: ...

    def reset(self) -> None: ...

    def close(self) -> None: ...


class SQLiteCaseStore:
    def __init__(self, db_path: str = "reports/cases.db") -> None:
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cases (
                    case_id TEXT PRIMARY KEY,
                    pattern TEXT,
                    accounts_json TEXT,
                    last_risk_score INTEGER,
                    last_risk_tier TEXT,
                    last_evidence TEXT,
                    first_seen TEXT,
                    last_seen TEXT,
                    times_seen INTEGER
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sightings (
                    case_id TEXT,
                    run_id TEXT,
                    seen_at TEXT,
                    UNIQUE(case_id, run_id)
                )
                """
            )

    def record_run(self, cases: list[dict], run_id: str) -> list[dict]:
        now = _now()
        enriched = []
        with self._connect() as conn:
            for case in cases:
                case_id = case["case_id"]
                accounts_json = json.dumps([str(a) for a in case.get("accounts", [])])

                conn.execute(
                    "INSERT OR IGNORE INTO sightings (case_id, run_id, seen_at) "
                    "VALUES (?, ?, ?)",
                    (case_id, run_id, now),
                )
                times_seen = conn.execute(
                    "SELECT COUNT(DISTINCT run_id) FROM sightings WHERE case_id = ?",
                    (case_id,),
                ).fetchone()[0]

                existing = conn.execute(
                    "SELECT first_seen FROM cases WHERE case_id = ?", (case_id,)
                ).fetchone()
                first_seen = existing["first_seen"] if existing else now

                conn.execute(
                    """
                    INSERT INTO cases (
                        case_id, pattern, accounts_json, last_risk_score,
                        last_risk_tier, last_evidence, first_seen, last_seen, times_seen
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(case_id) DO UPDATE SET
                        pattern = excluded.pattern,
                        accounts_json = excluded.accounts_json,
                        last_risk_score = excluded.last_risk_score,
                        last_risk_tier = excluded.last_risk_tier,
                        last_evidence = excluded.last_evidence,
                        last_seen = excluded.last_seen,
                        times_seen = excluded.times_seen
                    """,
                    (
                        case_id,
                        case.get("pattern", ""),
                        accounts_json,
                        case.get("risk_score", 0),
                        case.get("risk_tier", ""),
                        case.get("evidence", ""),
                        first_seen,
                        now,
                        times_seen,
                    ),
                )

                enriched.append(
                    {
                        **case,
                        "first_seen": first_seen,
                        "last_seen": now,
                        "times_seen": times_seen,
                    }
                )
        return enriched

    def all_cases(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM cases").fetchall()
        return [
            {
                "case_id": r["case_id"],
                "pattern": r["pattern"],
                "accounts": json.loads(r["accounts_json"]),
                "risk_score": r["last_risk_score"],
                "risk_tier": r["last_risk_tier"],
                "evidence": r["last_evidence"],
                "first_seen": r["first_seen"],
                "last_seen": r["last_seen"],
                "times_seen": r["times_seen"],
            }
            for r in rows
        ]

    def reset(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM cases")
            conn.execute("DELETE FROM sightings")

    def close(self) -> None:
        # Connections are opened per operation; nothing persistent to close.
        return None
