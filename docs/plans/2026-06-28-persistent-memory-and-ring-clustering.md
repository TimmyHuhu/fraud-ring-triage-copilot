# Persistent Memory and Ring Clustering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the fraud-triage app persistent cross-run case memory, recurring-ring recognition, Jaccard-based ring clustering, and an incremental replay mode, plus a larger synthetic dataset to demonstrate them.

**Architecture:** The existing four-agent pipeline is unchanged. Three new single-purpose modules are added downstream — `case_store.py` (SQLite persistence behind a `CaseStore` interface), `ring_linker.py` (Jaccard clustering), `stream.py` (batch splitting + run-id hashing) — and a seeded generator produces a scaled dataset. `app.py` wires these into new UI sections.

**Tech Stack:** Python 3.10+, Streamlit, pandas, numpy, NetworkX, stdlib `sqlite3`/`hashlib`/`json`, pytest.

## Global Constraints

- Python 3.10+ (CI runs 3.10, 3.11, 3.12). Use `from __future__ import annotations` only if needed; `list[dict]` syntax is fine on 3.10.
- **No new third-party dependencies.** Use stdlib `sqlite3`, `hashlib`, `json` and the already-declared `networkx`, `pandas`, `numpy`.
- All UTC timestamps use `datetime.now(timezone.utc)` (never `datetime.utcnow()`).
- Tests live under `tests/`, are named `test_*.py`, and run via `pytest` (repo `pytest.ini` sets `pythonpath = .`).
- Match existing style: plain module-level functions, type hints, no classes unless modeling state (the store is the one stateful class).
- Generated database file `reports/cases.db` is git-ignored. The generated CSV `data/large_sample_transactions.csv` IS committed.
- Commit messages: clean imperative style, each ending with:
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`

## File Structure

| File                                                     | Responsibility                                       |
| -------------------------------------------------------- | ---------------------------------------------------- |
| `agents/case_store.py` (create)                          | `CaseStore` protocol + `SQLiteCaseStore` persistence |
| `agents/ring_linker.py` (create)                         | `jaccard`, `cluster_cases`                           |
| `agents/stream.py` (create)                              | `compute_run_id`, `iter_batches`                     |
| `data/generate_sample_data.py` (create)                  | Seeded synthetic dataset generator                   |
| `data/large_sample_transactions.csv` (create, generated) | Scaled demo dataset                                  |
| `tests/test_case_store.py` (create)                      | Store behavior                                       |
| `tests/test_ring_linker.py` (create)                     | Clustering behavior                                  |
| `tests/test_stream.py` (create)                          | Batch splitting + run-id                             |
| `tests/test_large_dataset.py` (create)                   | Dataset → pipeline → clustering integration          |
| `app.py` (modify)                                        | Persistence, replay mode, new UI sections            |
| `.gitignore` (modify)                                    | Ignore `reports/*.db`                                |
| `README.md` (modify)                                     | Document new capabilities                            |

---

### Task 1: Persistent case store (`agents/case_store.py`)

**Files:**

- Create: `agents/case_store.py`
- Test: `tests/test_case_store.py`

**Interfaces:**

- Consumes: case dicts shaped like `risk_ranker` output (`case_id`, `pattern`, `accounts` list, `risk_score`, `risk_tier`, `evidence`).
- Produces:
  - `class SQLiteCaseStore(db_path: str = "reports/cases.db")`
  - `.record_run(cases: list[dict], run_id: str) -> list[dict]` — returns each case enriched with `first_seen`, `last_seen`, `times_seen`.
  - `.all_cases() -> list[dict]` — keys: `case_id`, `pattern`, `accounts` (list), `risk_score`, `risk_tier`, `evidence`, `first_seen`, `last_seen`, `times_seen`.
  - `.reset() -> None`, `.close() -> None`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_case_store.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_case_store.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agents.case_store'`

- [ ] **Step 3: Write the implementation**

```python
# agents/case_store.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_case_store.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add agents/case_store.py tests/test_case_store.py
git commit -m "Add SQLite case store for cross-run fraud memory

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Ring clustering (`agents/ring_linker.py`)

**Files:**

- Create: `agents/ring_linker.py`
- Test: `tests/test_ring_linker.py`

**Interfaces:**

- Consumes: case dicts with `case_id`, `accounts` (list), `pattern`, `risk_score`.
- Produces:
  - `jaccard(a: set, b: set) -> float`
  - `cluster_cases(cases: list[dict], threshold: float = 0.5) -> list[dict]` — each cluster has `cluster_id`, `case_ids` (sorted), `accounts` (sorted union), `patterns` (sorted distinct), `max_risk_score`, `size`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ring_linker.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_ring_linker.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agents.ring_linker'`

- [ ] **Step 3: Write the implementation**

```python
# agents/ring_linker.py
import hashlib

import networkx as nx


def jaccard(a: set, b: set) -> float:
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def _cluster_id(case_ids: list[str]) -> str:
    identity = "|".join(sorted(case_ids))
    digest = hashlib.sha1(identity.encode("utf-8")).hexdigest()
    return f"RING-{int(digest, 16) % 100000:05d}"


def cluster_cases(cases: list[dict], threshold: float = 0.5) -> list[dict]:
    account_sets = {
        case["case_id"]: {str(a) for a in case.get("accounts", [])}
        for case in cases
    }
    by_id = {case["case_id"]: case for case in cases}

    graph = nx.Graph()
    graph.add_nodes_from(account_sets.keys())

    case_ids = list(account_sets.keys())
    for i in range(len(case_ids)):
        for j in range(i + 1, len(case_ids)):
            a, b = case_ids[i], case_ids[j]
            if jaccard(account_sets[a], account_sets[b]) >= threshold:
                graph.add_edge(a, b)

    clusters = []
    for component in nx.connected_components(graph):
        members = sorted(component)
        accounts = sorted(set().union(*(account_sets[m] for m in members)))
        patterns = sorted({by_id[m].get("pattern", "") for m in members})
        max_risk = max((by_id[m].get("risk_score", 0) or 0) for m in members)
        clusters.append(
            {
                "cluster_id": _cluster_id(members),
                "case_ids": members,
                "accounts": accounts,
                "patterns": patterns,
                "max_risk_score": max_risk,
                "size": len(members),
            }
        )

    clusters.sort(key=lambda c: (c["max_risk_score"], c["cluster_id"]), reverse=True)
    return clusters
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ring_linker.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add agents/ring_linker.py tests/test_ring_linker.py
git commit -m "Add Jaccard ring clustering for related cases

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Batch splitting and run-id (`agents/stream.py`)

**Files:**

- Create: `agents/stream.py`
- Test: `tests/test_stream.py`

**Interfaces:**

- Produces:
  - `compute_run_id(data: bytes) -> str` — SHA-1 hex digest.
  - `iter_batches(df: pd.DataFrame, time_col: str, num_batches: int) -> list[pd.DataFrame]` — time-ordered contiguous chunks, all non-empty, rows preserved.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_stream.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_stream.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agents.stream'`

- [ ] **Step 3: Write the implementation**

```python
# agents/stream.py
import hashlib

import numpy as np
import pandas as pd


def compute_run_id(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def iter_batches(df: pd.DataFrame, time_col: str, num_batches: int) -> list[pd.DataFrame]:
    if num_batches < 1:
        raise ValueError("num_batches must be >= 1")

    working = df.copy()
    working["_parsed_time"] = pd.to_datetime(working[time_col], errors="coerce")

    valid = working.dropna(subset=["_parsed_time"]).sort_values("_parsed_time")
    invalid = working[working["_parsed_time"].isna()]
    ordered = pd.concat([valid, invalid]).drop(columns=["_parsed_time"])

    if ordered.empty:
        return []

    chunks = np.array_split(ordered, min(num_batches, len(ordered)))
    return [chunk.reset_index(drop=True) for chunk in chunks if not chunk.empty]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_stream.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add agents/stream.py tests/test_stream.py
git commit -m "Add stream batch splitting and run-id hashing

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Synthetic dataset generator (`data/generate_sample_data.py`)

**Files:**

- Create: `data/generate_sample_data.py`
- Create (generated): `data/large_sample_transactions.csv`
- Test: `tests/test_large_dataset.py`

**Interfaces:**

- Consumes: `run_pattern_finder` (Task uses existing), `run_risk_ranker` (existing), `cluster_cases` (Task 2).
- Produces: `generate() -> pd.DataFrame` with columns `sender, receiver, amount, timestamp`; `main()` writes the CSV.

**Design note:** Background traffic is customers (`C###`) paying merchants (`M##`) — a one-way bipartite flow with no cycles, so the only circular flows come from the planted rings. Each ring group shares accounts across a circular flow, a low-value pattern, and high-volume `AC-` pairs, so multiple findings over overlapping accounts cluster together.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_large_dataset.py
from agents.pattern_finder import run_pattern_finder
from agents.risk_ranker import run_risk_ranker
from agents.ring_linker import cluster_cases
from data.generate_sample_data import generate


def test_generated_dataset_has_expected_schema():
    df = generate()
    assert list(df.columns) == ["sender", "receiver", "amount", "timestamp"]
    assert len(df) > 1000


def test_generated_dataset_is_deterministic():
    a = generate()
    b = generate()
    assert a.equals(b)


def test_generated_dataset_produces_clusters():
    df = generate()
    result = run_pattern_finder(df)
    assert result["status"] == "success"
    assert result["num_findings"] >= 3
    cases = run_risk_ranker(result["findings"])["cases"]
    clusters = cluster_cases(cases, threshold=0.5)
    assert any(c["size"] >= 2 for c in clusters)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_large_dataset.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'data.generate_sample_data'`

- [ ] **Step 3: Write the implementation**

```python
# data/generate_sample_data.py
"""Generate a deterministic, larger synthetic transaction dataset.

Run: python data/generate_sample_data.py
Writes data/large_sample_transactions.csv.
"""
import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

SEED = 42
START = datetime(2026, 6, 1, 9, 0, 0)
OUTPUT = Path(__file__).parent / "large_sample_transactions.csv"


def _ts(offset_minutes: int) -> str:
    return (START + timedelta(minutes=offset_minutes)).strftime("%Y-%m-%d %H:%M:%S")


def generate() -> pd.DataFrame:
    rng = random.Random(SEED)
    rows: list[tuple] = []
    minute = 0

    # Background: customers paying merchants (one-way, no cycles).
    customers = [f"C{idx:03d}" for idx in range(250)]
    merchants = [f"M{idx:02d}" for idx in range(30)]
    for _ in range(2000):
        sender = rng.choice(customers)
        receiver = rng.choice(merchants)
        amount = rng.randint(50, 5000)
        rows.append((sender, receiver, amount, _ts(minute)))
        minute += rng.randint(1, 5)

    # Planted fraud rings. Each group shares accounts across multiple patterns
    # so the resulting cases cluster under Jaccard >= 0.5.
    ring_groups = [
        ["AC-100", "AC-101", "AC-102"],
        ["AC-200", "AC-201", "AC-202"],
        ["AC-300", "AC-301", "AC-302"],
    ]
    for a, b, c in ring_groups:
        # Repeated circular flow a -> b -> c -> a (also creates high-volume
        # AC- pairs that the track-02 detector flags).
        for _ in range(12):
            base = rng.randint(400, 600)
            rows.append((a, b, base, _ts(minute))); minute += 1
            rows.append((b, c, base - rng.randint(0, 30), _ts(minute))); minute += 1
            rows.append((c, a, base - rng.randint(0, 30), _ts(minute))); minute += 1
        # Repeated low-value transfers between two accounts already in the loop.
        for _ in range(8):
            rows.append((b, c, rng.randint(5, 20), _ts(minute))); minute += 1

    return pd.DataFrame(rows, columns=["sender", "receiver", "amount", "timestamp"])


def main() -> None:
    df = generate()
    df.to_csv(OUTPUT, index=False)
    print(f"Wrote {len(df)} rows to {OUTPUT}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_large_dataset.py -v`
Expected: 3 passed

If `test_generated_dataset_produces_clusters` fails (no size>=2 cluster), the
overlap is too weak — lower the demo by adding a second low-value pattern on a
different in-loop pair (e.g. `(a, b, ...)`) so two findings share two accounts.

- [ ] **Step 5: Generate the committed CSV**

Run: `python data/generate_sample_data.py`
Expected: `Wrote <N> rows to .../data/large_sample_transactions.csv`

- [ ] **Step 6: Commit**

```bash
git add data/generate_sample_data.py data/large_sample_transactions.csv tests/test_large_dataset.py
git commit -m "Add seeded large synthetic dataset and generator

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Wire persistence, replay, and new UI sections into `app.py`

**Files:**

- Modify: `app.py`
- Modify: `.gitignore`

**Interfaces:**

- Consumes: `SQLiteCaseStore` (Task 1), `cluster_cases` (Task 2), `compute_run_id` + `iter_batches` (Task 3), existing `run_pattern_finder`/`run_risk_ranker`/`run_action_recommender`/`run_report_writer`.

**Note:** Streamlit UI is verified manually (it runs the script top-to-bottom on
each interaction). The testable logic it depends on is already covered by Tasks
1–3. Keep the existing single-batch report flow intact; add persistence after it
and a separate replay branch.

- [ ] **Step 1: Ignore the generated database**

Add to `.gitignore`:

```
reports/*.db
```

- [ ] **Step 2: Add imports and store initialization**

At the top of `app.py`, after the existing `from agents.memory import ...` line,
add:

```python
import os

from agents.case_store import SQLiteCaseStore
from agents.ring_linker import cluster_cases
from agents.stream import compute_run_id, iter_batches
```

After `load_dotenv()`, add a cached store factory and a degrade-safe accessor:

```python
@st.cache_resource
def get_case_store():
    """Open the persistent case store once per Streamlit session.

    Returns None (and the app continues without persistence) if the database
    cannot be opened.
    """
    try:
        path = os.getenv("CASE_STORE_PATH", "reports/cases.db")
        return SQLiteCaseStore(path)
    except Exception as exc:  # pragma: no cover - defensive UI path
        st.warning(f"Persistent memory unavailable: {exc}")
        return None


store = get_case_store()
```

- [ ] **Step 3: Add a mode selector and replay helper**

Immediately after the `uploaded_file = st.file_uploader(...)` block, add:

```python
analysis_mode = st.radio(
    "Analysis mode",
    ["Single batch", "Replay (incremental)"],
    horizontal=True,
    help=(
        "Replay sorts the data by time and feeds it in chunks, accumulating "
        "investigation memory across runs."
    ),
)
num_batches = 1
if analysis_mode == "Replay (incremental)":
    num_batches = st.slider("Number of replay batches", 2, 10, 5)
```

Add this helper function near the top of `app.py` (after `store = get_case_store()`):

```python
def analyze_batch(batch_df):
    """Run pattern + risk ranking on one batch and return its ranked cases."""
    result = run_pattern_finder(batch_df)
    if result["status"] != "success" or not result["findings"]:
        return []
    return run_risk_ranker(result["findings"])["cases"]
```

- [ ] **Step 4: Persist single-batch results**

In the `if result["status"] == "success":` branch, after the existing
`save_trace(trace_events)` call (around the line that sets
`suspicious_cases_count = ranked_result["num_cases"]`), add:

```python
        if store is not None and analysis_mode == "Single batch":
            run_id = compute_run_id(df.to_csv(index=False).encode("utf-8"))
            store.record_run(ranked_result["cases"], run_id)
```

- [ ] **Step 5: Add the replay branch**

Replace the single top-level `if uploaded_file is not None:` guard so that
replay runs its own loop. Right after reading `df = pd.read_csv(uploaded_file)`
near the top of that block, add a short-circuit for replay mode:

```python
    if analysis_mode == "Replay (incremental)" and store is not None:
        cols = run_pattern_finder(df)["columns"]
        time_col = cols.get("timestamp") or "timestamp"
        batches = iter_batches(df, time_col, num_batches)

        st.subheader("Replay (Incremental Ingestion)")
        progress_rows = []
        for index, batch in enumerate(batches, start=1):
            cases = analyze_batch(batch)
            run_id = compute_run_id(batch.to_csv(index=False).encode("utf-8"))
            store.record_run(cases, run_id)
            high = sum(1 for c in cases if c["risk_tier"] == "High")
            progress_rows.append(
                {
                    "batch": index,
                    "transactions": len(batch),
                    "cases_found": len(cases),
                    "high_risk": high,
                }
            )
        st.dataframe(pd.DataFrame(progress_rows), use_container_width=True)
        st.success(
            f"Replayed {len(batches)} batches into persistent memory."
        )
```

This block runs and then falls through to the shared "Persistent Memory"
sections added in Step 6. Wrap the original single-batch rendering (the metrics,
preview, per-agent sections) in `if analysis_mode == "Single batch":` so it does
not also run during replay.

- [ ] **Step 6: Add Persistent Memory, Recurring Rings, and Ring Clusters sections**

After the per-mode rendering, still inside `if uploaded_file is not None:`, add:

```python
    if store is not None:
        st.divider()
        st.subheader("Persistent Memory")
        st.caption(
            "Cross-run case memory backed by SQLite via the CaseStore interface "
            "(the concrete seam for a future Cognee implementation)."
        )

        all_cases = store.all_cases()
        col_a, col_b = st.columns(2)
        col_a.metric("Cases remembered", len(all_cases))
        col_b.metric(
            "Recurring rings",
            sum(1 for c in all_cases if c["times_seen"] > 1),
        )

        recurring = [c for c in all_cases if c["times_seen"] > 1]
        if recurring:
            st.markdown("**Recurring Rings (seen in more than one run)**")
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "case_id": c["case_id"],
                            "pattern": c["pattern"],
                            "risk_tier": c["risk_tier"],
                            "times_seen": c["times_seen"],
                            "first_seen": c["first_seen"],
                            "last_seen": c["last_seen"],
                            "accounts": ", ".join(map(str, c["accounts"])),
                        }
                        for c in recurring
                    ]
                ).astype(str),
                use_container_width=True,
            )

        threshold = st.slider("Ring cluster similarity threshold", 0.1, 1.0, 0.5)
        clusters = cluster_cases(all_cases, threshold=threshold)
        multi = [c for c in clusters if c["size"] > 1]
        st.markdown(f"**Ring Clusters** ({len(multi)} multi-case clusters)")
        if clusters:
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "cluster_id": c["cluster_id"],
                            "size": c["size"],
                            "max_risk_score": c["max_risk_score"],
                            "patterns": ", ".join(c["patterns"]),
                            "case_ids": ", ".join(c["case_ids"]),
                            "accounts": ", ".join(map(str, c["accounts"])),
                        }
                        for c in clusters
                    ]
                ).astype(str),
                use_container_width=True,
            )

        if st.button("Reset persistent memory"):
            store.reset()
            st.success("Persistent memory cleared. Re-run to repopulate.")
```

- [ ] **Step 7: Verify the app compiles and imports**

Run: `python -m py_compile app.py`
Expected: no output (success)

Run: `python -c "import ast; ast.parse(open('app.py').read()); print('app.py parses')"`
Expected: `app.py parses`

- [ ] **Step 8: Manual verification (Streamlit)**

Run: `python -m streamlit run app.py`

Verify in the browser:

1. Upload `data/large_sample_transactions.csv` in **Single batch** mode → report
   sections render; a "Persistent Memory" section shows cases remembered > 0.
2. Re-upload the same file → "Cases remembered" does NOT double; `times_seen`
   stays correct (idempotent run_id).
3. Switch to **Replay (incremental)**, choose 5 batches, upload the same file →
   a per-batch progress table appears; "Recurring rings" count becomes > 0 and a
   multi-case **Ring Cluster** appears.
4. Adjust the threshold slider down/up → cluster count changes.
5. Click **Reset persistent memory** → counts drop to 0.

- [ ] **Step 9: Run the full test suite**

Run: `pytest`
Expected: all tests pass (previous 25 + new ones).

- [ ] **Step 10: Commit**

```bash
git add app.py .gitignore
git commit -m "Wire persistent memory, replay, and ring clustering into the app

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Document the new capabilities in `README.md`

**Files:**

- Modify: `README.md`

- [ ] **Step 1: Reframe the headline description**

Replace the intro sentence:

```
Fraud Ring Triage Copilot is a multi-agent investigation dashboard that helps fraud analysts detect hidden fraud rings, rank suspicious cases, recommend next actions, and generate downloadable case reports.
```

with:

```
Fraud Ring Triage Copilot is a multi-agent investigation system that continuously prioritizes and clusters fraud signals across cases and time. It detects hidden fraud rings, ranks suspicious cases, recommends analyst actions, remembers cases across runs, links recurring rings, and generates downloadable case reports.
```

- [ ] **Step 2: Replace the "Cognee-Ready Shared Memory" section**

Replace that section's body with text that distinguishes the per-run trace from
the cross-run store and names the interface:

```markdown
## Persistent Memory and Ring Clustering

The app keeps two layers of memory:

- **Per-run agent trace** — a JSON log of the four-agent handoff for a single
  analysis run (see the Agent Trace / Shared Memory section in the dashboard).
- **Cross-run case store** — a persistent SQLite store (`reports/cases.db`)
  behind a `CaseStore` interface (`agents/case_store.py`). Every case is keyed by
  a stable ID derived from its pattern and accounts, so the same fraud ring is
  recognized when it reappears in a later run ("seen N times, first seen ...").

On top of the store, a **ring linker** (`agents/ring_linker.py`) clusters cases
whose account sets overlap (Jaccard similarity above an adjustable threshold),
surfacing related cases as a single investigation cluster.

The `CaseStore` interface is the concrete seam for the planned Cognee
integration: a `CogneeCaseStore` would implement the same methods and replace the
SQLite backend without changing the app.
```

- [ ] **Step 3: Add a Replay / Incremental Mode section**

Add after the new memory section:

```markdown
## Replay / Incremental Mode

Instead of analyzing a file in one shot, **Replay** sorts transactions by time
and feeds them through the pipeline in batches, accumulating results in the case
store. This demonstrates continuous ingestion: a ring detected in several batches
shows `times_seen > 1`, and clusters grow as batches arrive. Replay operates on
the data you upload (including the included synthetic dataset) — there is no
external live stream.
```

- [ ] **Step 4: Document the larger dataset**

Replace the "Demo Dataset" section body with:

````markdown
Two datasets are included:

- `data/sample_transactions.csv` — a tiny, hand-built example.
- `data/large_sample_transactions.csv` — a larger, seeded synthetic dataset
  (hundreds of accounts, several overlapping multi-pattern fraud rings, and
  background customer-to-merchant traffic) for demonstrating clustering and
  replay at scale. Regenerate it deterministically with:

  ```bash
  python data/generate_sample_data.py
  ```
````

```

- [ ] **Step 5: Update the project structure tree and demo flow**

In the project structure tree, add under `agents/`:

```

│ ├── case_store.py
│ ├── ring_linker.py
│ └── stream.py

```

add under `data/`:

```

│ ├── generate_sample_data.py
│ └── large_sample_transactions.csv

```

and add the three new test files under `tests/`. Append to the Demo Flow list:

```

7. Switch to Replay mode to ingest the data incrementally.
8. Review Persistent Memory: recurring rings and ring clusters across runs.

````

- [ ] **Step 6: Verify and commit**

Run: `python -m py_compile app.py && pytest`
Expected: all pass.

```bash
git add README.md
git commit -m "Document persistent memory, ring clustering, and replay mode

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
````

---

## Final verification (after all tasks)

- [ ] Run `pytest` — all tests pass.
- [ ] Run `python -m streamlit run app.py` and walk the Task 5 Step 8 checklist.
- [ ] Run `git status` — confirm `reports/cases.db` is NOT staged (git-ignored)
      and `data/large_sample_transactions.csv` IS committed.
- [ ] Push and confirm CI is green on Python 3.10–3.12.
