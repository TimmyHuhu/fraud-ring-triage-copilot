# Design: Persistent Case Memory, Ring Clustering, and Incremental Replay

Date: 2026-06-28
Status: Proposed

## Goal

Move the project from a one-shot "upload a CSV, get a report" batch tool toward a
system that **accumulates investigation memory across runs**, **recognizes when
the same fraud ring reappears over time**, and **clusters related cases** that
share accounts. A lightweight replay mode demonstrates incremental ingestion on
top of the same persistent store.

This deepens the existing four-agent pipeline; it does not replace it and does
not pivot the fraud domain into anything else.

## Non-goals

- No external integrations (GitHub, webhooks, SIEM). The system stays a
  self-contained fraud-triage tool.
- No fabricated "real usage" or "live stream" claims. Replay operates on user
  data or the included synthetic dataset, and the README says so plainly.
- No orchestration/workflow engine rewrite. The pipeline stays a sequential set
  of focused agents.

## Architecture

The current pipeline is unchanged:

```
df -> pattern_finder -> risk_ranker -> action_recommender -> report_writer
```

Three new, single-purpose modules are added downstream, plus a synthetic data
generator:

| Module                         | Responsibility                                        | Depends on               |
| ------------------------------ | ----------------------------------------------------- | ------------------------ |
| `agents/case_store.py`         | `CaseStore` interface + `SQLiteCaseStore` persistence | stdlib `sqlite3`, `json` |
| `agents/ring_linker.py`        | Jaccard-similarity clustering of cases into rings     | `networkx`               |
| `agents/stream.py`             | Split a dataset into time-ordered batches for replay  | `pandas`                 |
| `data/generate_sample_data.py` | Deterministic synthetic dataset generator             | `pandas` (seeded)        |

`agents/memory.py` (the per-run agent-handoff trace) is left as-is. The trace is
single-run; the case store is cross-run. The README will make this distinction
explicit.

### Why these boundaries

- **`CaseStore` is an interface**, so the README's "Cognee-ready" claim becomes a
  real seam: a future `CogneeCaseStore` implements the same methods and drops in.
- **Clustering is separate from persistence** so it can be tested on plain
  in-memory case lists with no database.
- **Batch splitting is a pure function** of a DataFrame, independent of Streamlit
  and of the store.

## Data model (SQLite)

Stored at `reports/cases.db` (git-ignored). Two tables:

```sql
CREATE TABLE cases (
    case_id         TEXT PRIMARY KEY,
    pattern         TEXT,
    accounts_json   TEXT,        -- JSON array of account ids
    last_risk_score INTEGER,
    last_risk_tier  TEXT,
    last_evidence   TEXT,
    first_seen      TEXT,        -- ISO timestamp
    last_seen       TEXT,
    times_seen      INTEGER
);

CREATE TABLE sightings (
    case_id  TEXT,
    run_id   TEXT,
    seen_at  TEXT,
    UNIQUE(case_id, run_id)
);
```

`times_seen` is derived as `COUNT(DISTINCT run_id)` for the case. The
`UNIQUE(case_id, run_id)` constraint is what makes re-analyzing the same data
(including Streamlit's full-script reruns) idempotent.

### `run_id` definition

`run_id` is the SHA-1 hex digest of the exact data slice being analyzed:

- Single-batch mode: `run_id = sha1(uploaded file bytes)`.
- Replay mode: one `run_id` per batch = `sha1(batch rows serialized)`.

Re-running identical data yields identical `run_id`s, so sightings are not
double-counted.

### `CaseStore` interface

```python
class CaseStore(Protocol):
    def record_run(self, cases: list[dict], run_id: str) -> list[dict]:
        """Persist this run's cases; return them enriched with
        first_seen / last_seen / times_seen. Idempotent per (case_id, run_id)."""

    def all_cases(self) -> list[dict]:
        """Return every persisted case (across all runs)."""

    def reset(self) -> None:
        """Clear all stored cases and sightings (used by the demo reset button)."""

    def close(self) -> None: ...
```

`SQLiteCaseStore(db_path)` creates the schema on first use and opens a
connection per operation (Streamlit-safe).

## Ring clustering (`ring_linker.py`)

```python
def jaccard(a: set[str], b: set[str]) -> float: ...

def cluster_cases(cases: list[dict], threshold: float = 0.5) -> list[dict]:
    """Build a graph over cases; connect two cases when the Jaccard similarity
    of their account sets >= threshold; return one cluster per connected
    component."""
```

Each returned cluster:

```python
{
    "cluster_id": "RING-00042",     # stable hash of sorted member case_ids
    "case_ids": [...],
    "accounts": [...],              # union of member accounts, sorted
    "patterns": [...],              # distinct patterns in the cluster
    "max_risk_score": 95,
    "size": 3,
}
```

Clustering runs over **all cases in the store**, not just the current run, so the
"investigation memory" grows and links over time. Connected components come from
`networkx`, keeping the logic deterministic and explainable.

## Incremental replay (`stream.py`)

```python
def iter_batches(df, time_col, num_batches) -> list[pd.DataFrame]:
    """Sort by time_col and split into num_batches contiguous, time-ordered
    chunks. Rows with unparseable timestamps go in a final batch."""
```

The app feeds each batch through the pipeline in order, recording each into the
store under its own `run_id`. This demonstrates accumulation: the same ring
detected in multiple batches has `times_seen > 1`, and clusters grow as batches
arrive.

## App flow (app.py additions)

After the existing report section:

1. **Mode selector**: "Single batch" (default) or "Replay (incremental)" with a
   batch-count input.
2. Run the pipeline (once, or per batch), and call `store.record_run(...)`.
3. Run `cluster_cases(store.all_cases(), threshold)` with `threshold` from a UI
   slider (default 0.5).
4. New UI sections:
   - **Persistent Memory** metrics: total remembered cases, total runs.
   - **Recurring Rings**: cases with `times_seen > 1`, showing first seen / last
     seen / count.
   - **Ring Clusters**: clusters over the full store, with members, account
     union, and max risk.
   - **Reset Memory** button → `store.reset()` for clean demos.

DB path comes from env (`CASE_STORE_PATH`, default `reports/cases.db`).

## Error handling

If the store cannot be opened or written (locked/corrupt DB), the app shows a
warning and continues without persistence for that run — the analysis and report
still work. This mirrors the existing graceful `missing_columns` degradation.

## Synthetic dataset

`data/generate_sample_data.py` (fixed seed) produces
`data/large_sample_transactions.csv`:

- A few hundred accounts over a multi-day time range.
- Several fraud rings whose account sets **overlap**, and where a ring exhibits
  more than one pattern (e.g., circular flow _and_ low-value structuring) so that
  Jaccard clustering produces meaningful multi-case rings at threshold 0.5.
- A majority of normal transactions as background noise.

Both the generator and the generated CSV are committed (the generator makes the
dataset reproducible and is itself a credibility signal). The original
`sample_transactions.csv` stays for the quick demo.

## Testing (extends the existing pytest suite)

- `test_case_store.py`: record→`all_cases` round trip; same `run_id` does not
  inflate `times_seen`; different `run_id` increments it; `first_seen` stable,
  `last_seen` advances; `reset` clears. Uses a `tmp_path` database.
- `test_ring_linker.py`: `jaccard` values; clustering of known overlapping sets
  at/below threshold; singletons; determinism of `cluster_id`.
- `test_stream.py`: `iter_batches` preserves all rows, is time-ordered, and
  yields the requested batch count.

CI already runs the suite on Python 3.10–3.12.

## Documentation

README updates (only after the features exist):

- Reframe the headline toward "continuously prioritizes and clusters fraud
  signals across cases and time."
- New sections: Persistent Memory & Ring Clustering, Replay / Incremental Mode,
  the synthetic dataset + generator.
- Make the trace (per-run) vs case store (cross-run) distinction explicit, and
  describe the `CaseStore` interface as the concrete Cognee seam.
- Update the project structure tree and demo flow.

## Out of scope / future work

- `CogneeCaseStore` implementing `CaseStore`.
- Graph visualization of clusters.
- Larger Kaggle dataset ingestion.
