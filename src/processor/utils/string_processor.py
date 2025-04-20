from ast import literal_eval


def parse_code_string(code: str):
    """
    Parses strings that represent code (SQL script, Python list, etc.)
    """
    if code.startswith("```"):
        code = code[3:]
    if code.endswith("```"):
        code = code[:-3]
    if code.startswith("python"):
        code = code[6:]
    elif code.startswith("sql"):
        code = code[3:]
    elif code.startswith("json"):
        code = code[4:]
    return literal_eval(code)
