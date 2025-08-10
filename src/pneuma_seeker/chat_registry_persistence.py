import duckdb
import os
from typing import Optional

DB_PATH = os.path.join(".", "pneuma_seeker_chat_registry.duckdb")


def init_registry_db():
    con = duckdb.connect(DB_PATH)
    con.execute(
        """
    CREATE TABLE IF NOT EXISTS user_chats (
        user_id TEXT,
        chat_id TEXT,
        chat_title TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(user_id, chat_id)
    )
    """
    )
    con.close()


def add_chat(user_id: str, chat_id: str, chat_title: Optional[str] = None):
    con = duckdb.connect(DB_PATH)
    con.execute(
        """
        INSERT OR IGNORE INTO user_chats (user_id, chat_id, chat_title) VALUES (?, ?, ?)
    """,
        (user_id, chat_id, chat_title),
    )
    con.close()


def rename_chat(user_id: str, chat_id: str, new_title: str):
    con = duckdb.connect(DB_PATH)
    con.execute(
        """
        UPDATE user_chats
        SET chat_title = ?
        WHERE user_id = ? AND chat_id = ?
    """,
        (new_title, user_id, chat_id),
    )
    con.close()


def remove_chat(user_id: str, chat_id: str):
    con = duckdb.connect(DB_PATH)
    con.execute(
        """
        DELETE FROM user_chats WHERE user_id = ? AND chat_id = ?
    """,
        (user_id, chat_id),
    )
    con.close()


def list_users() -> list[str]:
    con = duckdb.connect(DB_PATH)
    rows = con.execute("SELECT DISTINCT user_id FROM user_chats").fetchall()
    con.close()
    return [r[0] for r in rows]


def list_chats(user_id: str) -> list[tuple[str, str]]:
    con = duckdb.connect(DB_PATH)
    rows = con.execute(
        "SELECT chat_id, chat_title FROM user_chats WHERE user_id = ?", (user_id,)
    ).fetchall()
    con.close()
    return [(r[0], r[1]) for r in rows]
