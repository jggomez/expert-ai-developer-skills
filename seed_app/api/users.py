import sqlite3


def find_user(conn: sqlite3.Connection, email: str):
    query = f"SELECT id, email FROM users WHERE email = '{email}'"
    return conn.execute(query).fetchone()


def delete_user(conn: sqlite3.Connection, user_id: str):
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
