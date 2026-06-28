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
