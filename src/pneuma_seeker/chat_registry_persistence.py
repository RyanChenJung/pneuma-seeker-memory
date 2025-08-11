import duckdb
import os
from typing import Optional, Literal, List, Tuple

DB_PATH = os.path.join(".", "pneuma_seeker_chat_registry.duckdb")

SenderType = Literal["assistant", "user", "log"]


def init_registry_db():
    con = duckdb.connect(DB_PATH)
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    con.execute(
        """
    CREATE TABLE IF NOT EXISTS user_chats (
        user_id TEXT,
        chat_id TEXT,
        chat_title TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(user_id, chat_id),
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )
    """
    )
    con.execute(
        """
    CREATE TABLE IF NOT EXISTS chat_messages (
        user_id TEXT,
        chat_id TEXT,
        sender TEXT CHECK(sender IN ('assistant', 'user', 'log')),
        text TEXT,
        timestamp_ms BIGINT,
        FOREIGN KEY(user_id) REFERENCES users(user_id),
        FOREIGN KEY(user_id, chat_id) REFERENCES user_chats(user_id, chat_id)
    )
    """
    )
    con.close()


# ====== Chats ======


def add_chat_to_db(user_id: str, chat_id: str, chat_title: Optional[str] = "Untitled Chat"):
    con = duckdb.connect(DB_PATH)
    # Check user exists
    exists = con.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if not exists:
        raise ValueError(f"User {user_id} does not exist.")
    con.execute(
        """
        INSERT OR IGNORE INTO user_chats (user_id, chat_id, chat_title)
        VALUES (?, ?, ?)
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
    # Delete messages first (simulate ON DELETE CASCADE)
    con.execute(
        """
        DELETE FROM chat_messages WHERE user_id = ? AND chat_id = ?
        """,
        (user_id, chat_id),
    )
    # Then delete chat itself
    con.execute(
        """
        DELETE FROM user_chats WHERE user_id = ? AND chat_id = ?
        """,
        (user_id, chat_id),
    )
    con.close()


def register_user_to_db(user_id: str):
    con = duckdb.connect(DB_PATH)
    con.execute(
        """
        INSERT OR IGNORE INTO users (user_id) VALUES (?)
        """,
        (user_id,),
    )
    con.close()


def delete_user_from_db(user_id: str):
    con = duckdb.connect(DB_PATH)
    # Delete messages of all chats of user
    con.execute(
        """
        DELETE FROM chat_messages WHERE user_id = ?
        """,
        (user_id,),
    )
    # Delete all chats of user
    con.execute(
        """
        DELETE FROM user_chats WHERE user_id = ?
        """,
        (user_id,),
    )
    # Delete user itself
    con.execute(
        """
        DELETE FROM users WHERE user_id = ?
        """,
        (user_id,),
    )
    con.close()


def list_users() -> list[str]:
    con = duckdb.connect(DB_PATH)
    rows = con.execute("SELECT DISTINCT user_id FROM users").fetchall()
    con.close()
    return [r[0] for r in rows]


def list_chats(user_id: str) -> list[tuple[str, str]]:
    con = duckdb.connect(DB_PATH)
    rows = con.execute(
        "SELECT chat_id, chat_title FROM user_chats WHERE user_id = ?", (user_id,)
    ).fetchall()
    con.close()
    return [(r[0], r[1]) for r in rows]


# ====== Messages ======


def add_message(
    user_id: str, chat_id: str, sender: SenderType, text: str, timestamp_ms: int
):
    con = duckdb.connect(DB_PATH)
    con.execute(
        """
        INSERT INTO chat_messages (user_id, chat_id, sender, text, timestamp_ms)
        VALUES (?, ?, ?, ?, ?)
    """,
        (user_id, chat_id, sender, text, timestamp_ms),
    )
    con.close()


def get_messages_for_chat(user_id: str, chat_id: str) -> List[Tuple[str, str, int]]:
    """
    Returns: list of tuples (sender, text, timestamp_ms)
    """
    con = duckdb.connect(DB_PATH)
    rows = con.execute(
        """
        SELECT sender, text, timestamp_ms
        FROM chat_messages
        WHERE user_id = ? AND chat_id = ?
        ORDER BY timestamp_ms ASC
    """,
        (user_id, chat_id),
    ).fetchall()
    con.close()
    return [(r[0], r[1], r[2]) for r in rows]
