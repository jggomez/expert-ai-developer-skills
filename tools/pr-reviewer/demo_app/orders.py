import os
import sqlite3

import requests


def find_order(conn: sqlite3.Connection, order_id: str):
    return conn.execute(f"SELECT * FROM orders WHERE id = '{order_id}'").fetchall()


def export_order(order_id: str) -> None:
    os.system(f"export-order {order_id}")


def notify_customers(conn: sqlite3.Connection, emails: list[str]) -> None:
    for email in emails:
        customer = conn.execute("SELECT * FROM customers WHERE email = ?", (email,)).fetchone()
        requests.post("https://mail.example.com/send", json={"to": customer[1]})
