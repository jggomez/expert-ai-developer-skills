"""Track 43: every Stop gate rejects fake data in any changed production code, mobile Flutter and
backends included (the UI reality gate only covers web UI)."""
import json
import os
import shutil
import subprocess

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
P = os.path.join(ROOT, "plugins")
GATES = [
    os.path.join(P, "claude", "senior-dev", "hooks", "universal-quality-gate.js"),
    os.path.join(P, "antigravity", "senior-dev", "hooks", "universal-quality-gate.js"),
    os.path.join(P, "antigravity", "python-backend", "hooks", "stop-gate.js"),
    os.path.join(P, "antigravity", "senior-dev-flutter", "hooks", "flutter-stop-gate.js"),
]
FAKE = "class OrdersRepository {\n  List<Order> all() {\n    return [Order(id: 1, name: 'Latte')];\n  }\n}\n"
REAL = "class OrdersRepository {\n  Future<List<Order>> all() => api.getOrders();\n}\n"

pytestmark = pytest.mark.skipif(shutil.which("node") is None or shutil.which("python3") is None,
                                reason="node and python3 are required")


def _git(repo, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t.co", *args], cwd=repo, check=True,
                   capture_output=True)


@pytest.fixture
def mobile_app(tmp_path):
    # Arrange: a mobile-only Flutter app (no web/ folder), so the browser UI gate never applies
    app = tmp_path / "app"
    (app / "lib" / "data").mkdir(parents=True)
    (app / "pubspec.yaml").write_text("name: app\n")
    _git(app, "init", "-q")
    _git(app, "add", ".")
    _git(app, "commit", "-qm", "base")
    return app


def _stop(repo, hook):
    payload = {"hook_event_name": "Stop", "cwd": str(repo), "workspacePaths": [str(repo)], "session_id": "s1",
               "conversationId": "c1", "lastUserInput": "build orders", "stop_hook_active": False,
               "stopReason": "NO_TOOL_CALL"}
    env = dict(os.environ, TMPDIR=str(repo.parent), PATH="/usr/bin:/bin:" + os.path.dirname(shutil.which("node")))
    return subprocess.run(["node", hook], input=json.dumps(payload), capture_output=True, text=True, timeout=60,
                          env=env)


def _blocked(result):
    return result.returncode == 2 or '"block"' in result.stdout or '"deny"' in result.stdout


@pytest.mark.parametrize("hook", GATES)
def test_fake_data_layer_in_a_mobile_app_blocks_the_stop(mobile_app, hook):
    # Arrange
    (mobile_app / "lib" / "data" / "orders_repository.dart").write_text(FAKE)
    # Act
    result = _stop(mobile_app, hook)
    # Assert
    assert _blocked(result), result.stdout + result.stderr
    assert "FAKE DATA GATE" in result.stdout + result.stderr


@pytest.mark.parametrize("hook", GATES)
def test_a_real_data_layer_passes(mobile_app, hook):
    # Arrange
    (mobile_app / "lib" / "data" / "orders_repository.dart").write_text(REAL)
    # Act
    result = _stop(mobile_app, hook)
    # Assert
    assert "FAKE DATA GATE" not in result.stdout + result.stderr, result.stdout + result.stderr
