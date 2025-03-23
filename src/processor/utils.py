import json
from ast import literal_eval


def format_schema(df):
    schema = "col: " + " | ".join(df.columns)
    sample_row = 'sample row: ' + ' | '.join(df.iloc[0].astype(str))
    return f"{schema}\n{sample_row}"


def format_schema_with_samples(df, num_samples=3, random_seed=42):
    import numpy as np
    schema = "col: " + " | ".join(df.columns)
    np.random.seed(random_seed)
    if len(df) <= num_samples:
        sample_indices = range(len(df))
    else:
        sample_indices = np.random.choice(len(df), num_samples, replace=False)
    sample_rows = []
    for i, idx in enumerate(sample_indices):
        row_str = f"sample row {i+1}: " + " | ".join(df.iloc[idx].astype(str))
        sample_rows.append(row_str)
    return schema + "\n" + "\n".join(sample_rows)

def format_schema_extensive(df, start=0, end_exclusive=1):
    schema = "col: " + " | ".join(df.columns)
    sample_rows = []
    for idx, i in enumerate(range(start, end_exclusive)):
        row_str = f"row {idx+1}: " + " | ".join(df.iloc[i].astype(str))
        sample_rows.append(row_str)
    return schema + "\n" + "\n".join(sample_rows)


def parse_code_string(code: str):
    if code.startswith('```'):
        code = code[3:]
    if code.endswith('```'):
        code = code[:-3]
    if code.startswith('python'):
        code = code[6:]
    elif code.startswith('sql'):
        code = code[3:]
    return literal_eval(code)

def read_jsonl(file_path: str):
    data: list[dict[str, str]] = []
    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            data.append(json.loads(line.strip()))
    return data


def write_jsonl(data: list[dict[str, str]], file_path: str):
    with open(file_path, "w", encoding="utf-8") as file:
        for item in data:
            file.write(json.dumps(item))
            file.write("\n")
