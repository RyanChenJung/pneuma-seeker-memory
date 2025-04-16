from ast import literal_eval


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