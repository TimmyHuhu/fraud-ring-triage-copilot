import pandas as pd
import networkx as nx


def infer_columns(df: pd.DataFrame) -> dict:
    columns = {c.lower(): c for c in df.columns}

    sender_candidates = ["sender", "source", "from", "from_account", "origin", "payer", "account_from"]
    receiver_candidates = ["receiver", "target", "to", "to_account", "destination", "payee", "account_to"]
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


def find_circular_flows(df: pd.DataFrame, sender_col: str, receiver_col: str, amount_col: str, max_results: int = 10):
    graph = nx.DiGraph()

    for _, row in df.iterrows():
        sender = str(row[sender_col])
        receiver = str(row[receiver_col])
        amount = float(row[amount_col]) if pd.notna(row[amount_col]) else 0.0

        if sender != receiver:
            graph.add_edge(sender, receiver, amount=amount)

    cycles = []
    for cycle in nx.simple_cycles(graph):
        if 2 <= len(cycle) <= 4:
            cycle_edges = []
            total_amount = 0.0

            for i in range(len(cycle)):
                src = cycle[i]
                dst = cycle[(i + 1) % len(cycle)]
                edge_amount = graph[src][dst].get("amount", 0.0)
                total_amount += edge_amount
                cycle_edges.append(f"{src} → {dst}")

            cycles.append({
                "pattern": "circular_flow",
                "accounts": cycle,
                "evidence": " → ".join(cycle + [cycle[0]]),
                "num_accounts": len(cycle),
                "total_amount": round(total_amount, 2),
            })

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
        findings.append({
            "pattern": "repeated_low_value_transfers",
            "accounts": [str(row[sender_col]), str(row[receiver_col])],
            "evidence": f"{row['num_transactions']} low-value transfers from {row[sender_col]} to {row[receiver_col]}",
            "num_transactions": int(row["num_transactions"]),
            "total_amount": round(float(row["total_amount"]), 2),
            "avg_amount": round(float(row["avg_amount"]), 2),
        })

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

    findings = circular_findings + low_value_findings

    return {
        "status": "success",
        "columns": cols,
        "findings": findings,
        "num_findings": len(findings),
    }
