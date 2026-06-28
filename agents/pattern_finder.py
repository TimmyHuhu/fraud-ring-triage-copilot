import pandas as pd
import networkx as nx


def infer_columns(df: pd.DataFrame) -> dict:
    columns = {c.lower(): c for c in df.columns}

    sender_candidates = [
        "sender", "source", "from", "from_account", "origin", "payer",
        "account_from", "account_id",
    ]
    receiver_candidates = [
        "receiver", "target", "to", "to_account", "destination", "payee",
        "account_to", "counterparty_id",
    ]
    amount_candidates = ["amount", "transaction_amount", "value", "money", "amt"]
    time_candidates = ["timestamp", "time", "date", "transaction_time", "created_at"]

    def find_candidate(candidates):
        for candidate in candidates:
            for lower_col, original_col in columns.items():
                if candidate == lower_col or candidate in lower_col:
                    return original_col
        return None

    return {
        "sender": find_candidate(sender_candidates),
        "receiver": find_candidate(receiver_candidates),
        "amount": find_candidate(amount_candidates),
        "timestamp": find_candidate(time_candidates),
    }


def find_track02_account_ring(
    df: pd.DataFrame,
    sender_col: str,
    receiver_col: str,
    amount_col: str,
    min_pair_count: int = 10,
    min_pair_total: float = 5000,
) -> list[dict]:
    working = df.copy()
    working[amount_col] = pd.to_numeric(working[amount_col], errors="coerce")
    working = working.dropna(subset=[sender_col, receiver_col, amount_col])

    account_to_account = working[
        working[receiver_col].astype(str).str.startswith("AC-")
    ].copy()

    if account_to_account.empty:
        return []

    grouped = (
        account_to_account
        .groupby([sender_col, receiver_col])
        .agg(
            num_transactions=(amount_col, "count"),
            total_amount=(amount_col, "sum"),
            avg_amount=(amount_col, "mean"),
            min_amount=(amount_col, "min"),
            max_amount=(amount_col, "max"),
        )
        .reset_index()
    )

    suspicious_edges = grouped[
        (grouped["num_transactions"] >= min_pair_count)
        & (grouped["total_amount"] >= min_pair_total)
    ]

    if suspicious_edges.empty:
        return []

    accounts = sorted(
        set(suspicious_edges[sender_col].astype(str))
        | set(suspicious_edges[receiver_col].astype(str))
    )

    total_amount = float(suspicious_edges["total_amount"].sum())
    total_txns = int(suspicious_edges["num_transactions"].sum())

    edge_details = [
        (
            f"{row[sender_col]} → {row[receiver_col]}: "
            f"{int(row['num_transactions'])} txns, "
            f"${float(row['total_amount']):,.2f}"
        )
        for _, row in suspicious_edges.sort_values(
            "total_amount", ascending=False
        ).iterrows()
    ]

    return [
        {
            "pattern": "track02_account_counterparty_ring",
            "accounts": accounts,
            "evidence": (
                f"{total_txns} account-to-account transfers totaling "
                f"${total_amount:,.2f}. "
                + " | ".join(edge_details)
            ),
            "num_accounts": len(accounts),
            "num_transactions": total_txns,
            "total_amount": round(total_amount, 2),
            "edge_details": edge_details,
        }
    ]


def find_circular_flows(
    df: pd.DataFrame,
    sender_col: str,
    receiver_col: str,
    amount_col: str,
    max_results: int = 10,
):
    graph = nx.DiGraph()

    working = df.copy()
    working[amount_col] = pd.to_numeric(working[amount_col], errors="coerce")

    for _, row in working.iterrows():
        sender = str(row[sender_col])
        receiver = str(row[receiver_col])
        amount = float(row[amount_col]) if pd.notna(row[amount_col]) else 0.0

        if sender != receiver:
            graph.add_edge(sender, receiver, amount=amount)

    cycles = []

    for cycle in nx.simple_cycles(graph):
        if 2 <= len(cycle) <= 4:
            total_amount = 0.0

            for i in range(len(cycle)):
                src = cycle[i]
                dst = cycle[(i + 1) % len(cycle)]
                total_amount += graph[src][dst].get("amount", 0.0)

            # simple_cycles returns each cycle at an arbitrary rotation, so the
            # same loop can come back as [A, B, C] or [B, C, A] across runs.
            # Rotate to start at the smallest node for a stable representation.
            start = cycle.index(min(cycle))
            cycle = cycle[start:] + cycle[:start]

            cycles.append(
                {
                    "pattern": "circular_flow",
                    "accounts": cycle,
                    "evidence": " → ".join(cycle + [cycle[0]]),
                    "num_accounts": len(cycle),
                    "total_amount": round(total_amount, 2),
                }
            )

        if len(cycles) >= max_results:
            break

    return cycles


def find_repeated_low_value_transfers(
    df: pd.DataFrame,
    sender_col: str,
    receiver_col: str,
    amount_col: str,
    min_count: int = 3,
):
    working = df.copy()
    working[amount_col] = pd.to_numeric(working[amount_col], errors="coerce")
    working = working.dropna(subset=[amount_col])

    low_value_cutoff = working[amount_col].quantile(0.25)
    low_value = working[working[amount_col] <= low_value_cutoff]

    grouped = (
        low_value
        .groupby([sender_col, receiver_col])
        .agg(
            num_transactions=(amount_col, "count"),
            total_amount=(amount_col, "sum"),
            avg_amount=(amount_col, "mean"),
        )
        .reset_index()
    )

    suspicious = grouped[grouped["num_transactions"] >= min_count]

    findings = []

    for _, row in suspicious.iterrows():
        findings.append(
            {
                "pattern": "repeated_low_value_transfers",
                "accounts": [str(row[sender_col]), str(row[receiver_col])],
                "evidence": (
                    f"{row['num_transactions']} low-value transfers from "
                    f"{row[sender_col]} to {row[receiver_col]}"
                ),
                "num_transactions": int(row["num_transactions"]),
                "total_amount": round(float(row["total_amount"]), 2),
                "avg_amount": round(float(row["avg_amount"]), 2),
            }
        )

    return findings


def run_pattern_finder(df: pd.DataFrame):
    cols = infer_columns(df)

    if not cols["sender"] or not cols["receiver"] or not cols["amount"]:
        return {
            "status": "missing_columns",
            "columns": cols,
            "findings": [],
            "message": "Could not infer sender, receiver, and amount columns.",
        }

    track02_findings = find_track02_account_ring(
        df=df,
        sender_col=cols["sender"],
        receiver_col=cols["receiver"],
        amount_col=cols["amount"],
    )

    circular_findings = find_circular_flows(
        df=df,
        sender_col=cols["sender"],
        receiver_col=cols["receiver"],
        amount_col=cols["amount"],
    )

    low_value_findings = find_repeated_low_value_transfers(
        df=df,
        sender_col=cols["sender"],
        receiver_col=cols["receiver"],
        amount_col=cols["amount"],
    )

    findings = track02_findings + circular_findings + low_value_findings

    return {
        "status": "success",
        "columns": cols,
        "findings": findings,
        "num_findings": len(findings),
    }
