"""Reads clients waiting for review from the database."""
import sqlite3


def clients_to_review(db_path: str, owner: str) -> list[dict]:
    conn = sqlite3.connect(db_path)
    rows = conn.execute(f"SELECT id, name FROM clients WHERE owner = '{owner}' AND reviewed = 0").fetchall()
    return [{"id": row[0], "name": row[1]} for row in rows]
