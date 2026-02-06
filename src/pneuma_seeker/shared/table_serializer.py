import math

import numpy as np
import pandas as pd
from pandas import DataFrame


def _serialize_cell(value):
    if value is None:
        return None
    if pd.isna(value):
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, float) and (math.isinf(value) or math.isnan(value)):
        return None
    return value


def serialize_dataframe(df: DataFrame, nrows: int):
    # Convert DataFrame to a JSON-safe list of dicts
    safe_df = df.head(nrows).replace([np.inf, -np.inf], np.nan)
    records = safe_df.to_dict(orient="records")
    return [
        {key: _serialize_cell(value) for key, value in row.items()}
        for row in records
    ]
