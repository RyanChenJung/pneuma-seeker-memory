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
def old_approach():
    start = time.time()
    table = pd.read_csv("../buysite/dataset/JI_PURCHASE_ORDER_CUSTOM_FIELDS.csv")
    end = time.time()
    print(f"DATA LOADING TIME: {end-start} seconds!")
    start = time.time()
    print(f"categorical_column_info request with params: {args}")
    table_id: str | None = args.get("id")
    table_columns: list[str] | None = args.get("columns")
    if table_id is None:
        error_message = "The `id` field most not be empty."
        print(f"=> {error_message}")
    if table_columns is None:
        error_message = "The `columns` field most not be empty."
        print(f"=> {error_message}")
    if not isinstance(table_columns, list) or len(table_columns) == 0:
        error_message = "The `columns` field must be a non-empty list of strings (column names in the table)"
        print(f"=> {error_message}")

    for document in retrieved_tables:
        if "ji_purchase_order_custom_fields" == table_id:
            cat_col_info = ""
            for column in table_columns:
                if column not in table.columns:
                    cat_col_info += (
                        f"Column `{column}` does not exist in the table.\n"
                    )
                    continue

                counts = table[column].value_counts()
                top_values = counts.index[:10].tolist()

                # Append "truncated" if there are more than 10 unique values
                if len(counts) > 10:
                    top_values.append("truncated")

                # Convert list to string for cleaner display
                top_values_str = ", ".join(str(v) for v in top_values)
                column_info = f"{column}: {top_values_str}\n"
                cat_col_info += column_info
    end = time.time()
    print(f"TOTAL TIME: {end-start} seconds!")

old_approach()