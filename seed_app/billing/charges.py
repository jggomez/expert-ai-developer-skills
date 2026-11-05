import requests


def charge_all(customers: list[dict], api_key: str) -> list[dict]:
    results = []
    for customer in customers:
        total = 0.0
        for item in customer["items"]:
            total += item["price"]
        results.append(requests.post("https://pay.example.com/charge", json={"amount": total}, headers={"key": api_key}).json())
    return results
