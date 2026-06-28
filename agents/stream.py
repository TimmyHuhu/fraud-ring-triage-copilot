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

    # Split on integer positions (not the DataFrame itself) to avoid numpy's
    # deprecated swapaxes path when array_split is given a DataFrame.
    index_groups = np.array_split(np.arange(len(ordered)), min(num_batches, len(ordered)))
    return [
        ordered.iloc[group].reset_index(drop=True)
        for group in index_groups
        if len(group) > 0
    ]
