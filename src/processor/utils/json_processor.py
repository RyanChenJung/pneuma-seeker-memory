import json
from typing import Any

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

def parse_json(json_string: str) -> Any:
    if json_string.startswith("```"):
        json_string = json_string[3:]
    if json_string.endswith("```"):
        json_string = json_string[:-3]
    if json_string.startswith("json"):
        json_string = json_string[4:]
    return json.loads(json_string)

def parse_sql(sql_string: str) -> str:
    if sql_string.startswith("```"):
        sql_string = sql_string[3:]
    if sql_string.endswith("```"):
        sql_string = sql_string[:-3]
    if sql_string.startswith("sql"):
        sql_string = sql_string[3:]
    return sql_string
