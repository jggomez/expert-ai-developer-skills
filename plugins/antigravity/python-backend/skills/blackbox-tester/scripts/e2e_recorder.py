"""Records what a Playwright test really did, for check_evidence.py. Copy to tests/e2e/.

    run = RunRecorder(page, "docs/<feature-name>/evidence")
    # ...drive the app, then compare the screen with the source...
    run.data_check("source-on-screen", "order 42 from GET /api/orders is listed")
    run.data_check("persisted-after-reload", "the new order is still listed")
    run.save()
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path


class RunRecorder:
    def __init__(self, page, evidence_dir: str, **details) -> None:
        self._page = page
        self._evidence_dir = Path(evidence_dir)
        self._responses: list = []
        self.manifest: dict = {"version": 1, "pages": [], "requests": [], "dataChecks": [], **details}
        page.on("framenavigated", self._on_navigation)
        page.on("response", self._responses.append)

    def _on_navigation(self, frame) -> None:
        if frame == self._page.main_frame:
            self.manifest["pages"].append(frame.url)

    def data_check(self, kind: str, detail: str) -> None:
        self.manifest["dataChecks"].append({"kind": kind, "detail": detail})

    def save(self) -> Path:
        # Stubbed and service-worker responses have no server address.
        self.manifest["requests"] = [
            {
                "method": r.request.method,
                "url": r.url,
                "status": r.status,
                "resourceType": r.request.resource_type,
                "remote": bool(r.server_addr()) and not r.from_service_worker,
            }
            for r in self._responses
        ]
        self._evidence_dir.mkdir(parents=True, exist_ok=True)
        path = self._evidence_dir / f"run-{uuid.uuid4()}.json"
        path.write_text(json.dumps(self.manifest, indent=2), encoding="utf-8")
        return path
