import sqlite3

from pandas import DataFrame

def execute_query(tables: list[DataFrame], query: str):
    conn = sqlite3.connect(':memory:')
    
