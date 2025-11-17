import os
import duckdb
import time
import pandas as pd

from memory_profiler import profile

args = {
    "id": "ji_purchase_order_custom_fields",
    "columns": ["split_amount_business_currency"]
}
data_sources = ["buysite"]
DB_BACKEND_PATH = "."
retrieved_tables = ["ji_purchase_order_custom_fields"]

@profile
def new_approach():
    start = time.time()
    with duckdb.connect("buysite.db", read_only=True) as con:
        table = con.execute("SELECT * FROM ji_purchase_order_custom_fields LIMIT 5").fetchdf()
    end = time.time()
    print(f"DATA LOADING TIME: {end-start} seconds")

    start = time.time()
    if isinstance(args, dict):
        print(f"Column Info Extractor request with params: {args}")
        table_id: str | None = args.get("id")
        table_columns: list[str] | None = args.get("columns")
        if table_id is None:
            msg = "The `id` field must not be empty."
            print(f"=> {msg}")

        if table_columns is None:
            msg = "The `columns` field must not be empty."
            print(f"=> {msg}")

        if not isinstance(table_columns, list) or len(table_columns) == 0:
            msg = (
                "The `columns` field must be a non-empty list of valid column name strings."
            )
            print(f"=> {msg}")

        table_exists = any(i == table_id for i in retrieved_tables)
        if not table_exists:
            msg = (
                f"ID {table_id} does not exist in retrieval results; "
                f"ensure it exists in the current retrieval results."
            )
            print(msg)

        info_output = f"Column information for table `{table_id}`:\n"
        found_in_any_db = False
        try:
            for data_source in data_sources:
                db_path = os.path.join(DB_BACKEND_PATH, f"{data_source}.db")

                with duckdb.connect(db_path, read_only=True) as con:
                    exists_check = con.execute(
                        "SELECT table_name FROM information_schema.tables WHERE table_name = ?",
                        [table_id],
                    ).fetchall()

                    if len(exists_check) == 0:
                        continue

                    found_in_any_db = True
                    schema_df = con.execute(f"PRAGMA table_info('{table_id}');").fetchdf()
                    schema_lookup = dict(zip(schema_df["name"], schema_df["type"]))

                    for col in table_columns:
                        if col not in schema_lookup:
                            info_output += f"- `{col}`: Column does not exist.\n"
                            continue

                        duck_type = schema_lookup[col].lower()
                        is_numeric = any(
                            t in duck_type
                            for t in [
                                "int",
                                "decimal",
                                "double",
                                "real",
                                "float",
                            ]
                        )

                        if is_numeric:
                            stats_query = f"""
                                SELECT 
                                    COUNT(*) AS count,
                                    MIN("{col}") AS min,
                                    MAX("{col}") AS max,
                                    AVG("{col}") AS mean,
                                    STDDEV("{col}") AS stddev,
                                    QUANTILE_CONT("{col}", 0.25) AS q25,
                                    QUANTILE_CONT("{col}", 0.50) AS median,
                                    QUANTILE_CONT("{col}", 0.75) AS q75
                                FROM "{table_id}";
                            """
                            stats = con.execute(stats_query).fetchdf().iloc[0]

                            info_output += (
                                f"- `{col}` (numeric):\n"
                                f"    count = {stats['count']}\n"
                                f"    min = {stats['min']}\n"
                                f"    max = {stats['max']}\n"
                                f"    mean = {stats['mean']}\n"
                                f"    stddev = {stats['stddev']}\n"
                                f"    q25 = {stats['q25']}\n"
                                f"    median = {stats['median']}\n"
                                f"    q75 = {stats['q75']}\n"
                            )
                            continue

                        unique_count_query = f"""
                            SELECT COUNT(DISTINCT "{col}") FROM "{table_id}";
                        """
                        unique_count = con.execute(unique_count_query).fetchone()[0]

                        topk = 10
                        topk_query = f"""
                            SELECT "{col}" AS value, COUNT(*) AS count
                            FROM "{table_id}"
                            GROUP BY "{col}"
                            ORDER BY count DESC
                            LIMIT {topk};
                        """
                        df_top = con.execute(topk_query).fetchdf()

                        values = df_top["value"].tolist()
                        topk_count = len(values)
                        if unique_count > topk_count:
                            remaining = unique_count - topk_count
                            values.append(f"truncated ({remaining} values left)")

                        values_str = ", ".join(str(v) for v in values)
                        info_output += f"- `{col}` (categorical): {values_str}\n"

                    break

                if not found_in_any_db:
                    msg = f"Table `{table_id}` does not exist in any available data source."
                    print(msg)

        except Exception as e:
            msg = f"Error computing column info: {e}"
            print(msg)

        print(info_output)
    else:
        msg = "Argument must be a dict with keys: `id`, `columns`."
        print(msg)
    end = time.time()
    print(f"TOTAL TIME: {end-start} seconds!") 

new_approach()