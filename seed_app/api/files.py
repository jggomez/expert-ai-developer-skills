from pathlib import Path


def read_report(name: str) -> str:
    return Path(f"/srv/reports/{name}").read_text()
