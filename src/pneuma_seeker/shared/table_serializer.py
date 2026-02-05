from pandas import DataFrame


def serialize_dataframe(df: DataFrame, nrows: int):
    # Convert DataFrame to a JSON-safe list of dicts
    return (
        df.head(nrows)
        .map(lambda x: x.isoformat() if hasattr(x, "isoformat") else x)
        .to_dict(orient="records")
    )
