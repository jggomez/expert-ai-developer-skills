"""Tests for skills/compliance-verifier/scripts/check_fake_data.py.

A green test suite says nothing about a screen that paints invented data, so this deterministic
check rejects fake data added to production UI code. Test code and approved demos stay allowed.
"""
import os
import subprocess
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPT = os.path.join(ROOT, "skills", "compliance-verifier", "scripts", "check_fake_data.py")


def _git(repo, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t.co", *args], cwd=repo, check=True,
                   capture_output=True)


@pytest.fixture
def repo(tmp_path):
    _git(tmp_path, "init", "-q")
    (tmp_path / "README.md").write_text("base\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "base")
    return tmp_path


def _write(repo, rel, text):
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _run(repo, *args):
    return subprocess.run([sys.executable, SCRIPT, "--repo", str(repo), *args], capture_output=True, text=True,
                          timeout=30)


@pytest.mark.parametrize("line", [
    "const users = mockUsers;",
    "const MOCK_ORDERS = [];",
    "const rows = getFakeData();",
    "const sampleData = [];",
    "const name = 'John Doe';",
    "const bio = 'Lorem ipsum dolor';",
    "const mail = 'ana@example.com';",
    "import { faker } from '@faker-js/faker';",
    "import { setupWorker } from 'msw/browser';",
    "const price = Math.random() * 100;",
])
def test_rejects_fake_data_in_production_ui_code(repo, line):
    # Arrange
    _write(repo, "src/pages/Users.tsx", f"{line}\n")
    # Act
    result = _run(repo)
    # Assert
    assert result.returncode == 1, result.stdout
    assert "src/pages/Users.tsx:1" in result.stdout


def test_rejects_literals_returned_after_a_simulated_delay(repo):
    # Arrange
    _write(repo, "lib/data/items.dart",
           "Future<List<String>> load() async {\n  await Future.delayed(const Duration(seconds: 1));\n"
           "  return ['Item A', 'Item B'];\n}\n")
    # Act
    result = _run(repo)
    # Assert
    assert result.returncode == 1, result.stdout
    assert "simulated" in result.stdout


@pytest.mark.parametrize("rel", [
    "tests/e2e/users.spec.ts", "src/pages/Users.test.tsx", "src/__mocks__/users.ts", "test/users_test.dart",
    "integration_test/app_test.dart", "src/fixtures/users.ts", "src/pages/Users.stories.tsx", "db/seeds/users.ts",
])
def test_ignores_test_code_and_seeds(repo, rel):
    # Arrange
    _write(repo, rel, "const users = mockUsers; // John Doe\n")
    # Act
    result = _run(repo)
    # Assert
    assert result.returncode == 0, result.stdout


def test_passes_with_a_real_data_source(repo):
    # Arrange
    _write(repo, "src/pages/Users.tsx", "const users = await fetch('/api/users').then((r) => r.json());\n")
    # Act
    result = _run(repo)
    # Assert
    assert result.returncode == 0, result.stdout
    assert "PASS" in result.stdout


def test_allows_example_addresses_in_input_hints(repo):
    # Arrange
    _write(repo, "src/Login.tsx", '<input placeholder="you@example.com" />\n')
    _write(repo, "lib/login.dart", "const decoration = InputDecoration(hintText: 'you@example.com');\n")
    # Act
    result = _run(repo)
    # Assert
    assert result.returncode == 0, result.stdout


def test_only_looks_at_added_lines(repo):
    # Arrange: the fake data is old; this change does not add it
    _write(repo, "src/Old.tsx", "const users = mockUsers;\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "old")
    _write(repo, "src/Old.tsx", "const users = mockUsers;\nconst total = users.length;\n")
    # Act
    result = _run(repo)
    # Assert
    assert result.returncode == 0, result.stdout


def test_compares_against_a_base_branch(repo):
    # Arrange
    _git(repo, "checkout", "-qb", "feature")
    _write(repo, "src/New.tsx", "const users = mockUsers;\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "feature")
    # Act
    result = _run(repo, "--base", "HEAD~1")
    # Assert
    assert result.returncode == 1, result.stdout


def test_a_demo_marker_without_approval_in_the_plan_is_rejected(repo):
    # Arrange
    _write(repo, "src/Demo.tsx", "// demo-data: approved\nconst users = mockUsers;\n")
    # Act
    result = _run(repo)
    # Assert
    assert result.returncode == 1, result.stdout


def test_a_demo_approved_in_the_plan_is_allowed(repo):
    # Arrange
    _write(repo, "src/Demo.tsx", "// demo-data: approved\nconst users = mockUsers;\n")
    _write(repo, "PLAN.md", "| Users | none yet | src/Demo.tsx | demo-data: approved by the user |\n")
    # Act
    result = _run(repo)
    # Assert
    assert result.returncode == 0, result.stdout


def test_outside_a_git_repository_is_a_usage_error(tmp_path):
    # Act
    result = _run(tmp_path)
    # Assert
    assert result.returncode == 2


@pytest.mark.parametrize("rel", [
    ".claude/plugins/senior-dev/hooks/universal-quality-gate.js",
    ".agents/rules/ui.js",
    "node_modules/pkg/index.js",
    ".venv/lib/site-packages/pkg/static/app.js",
    "docs/items/evidence/report.html",
    "vendor/lib/widget.js",
])
def test_ignores_agent_plugins_docs_and_dependency_folders(repo, rel):
    # Arrange: these folders never hold the app's UI, and plugin comments talk about mock data
    _write(repo, rel, "// rejects mock or fake data in the UI\nconst mockUsers = [];\n")
    # Act
    result = _run(repo)
    # Assert
    assert result.returncode == 0, result.stdout


def test_a_demo_approved_in_the_feature_folder_plan_is_allowed(repo):
    # Arrange
    _write(repo, "src/Demo.tsx", "// demo-data: approved\nconst users = mockUsers;\n")
    _write(repo, "docs/users/PLAN.md", "| Users | none yet | src/Demo.tsx | demo-data: approved by the user |\n")
    # Act
    result = _run(repo)
    # Assert
    assert result.returncode == 0, result.stdout


# Track 43: fakes hide below the screen, in data layers and backends, under believable names.
@pytest.mark.parametrize("rel,line", [
    ("lib/data/orders_repository.dart", "    return [Order(id: 1, name: 'Latte')];"),
    ("lib/features/orders/order_service.dart", "  return const [Order(id: 1, name: 'Latte')];"),
    ("app/repositories/orders.py", "    return [{'id': 1, 'name': 'Latte'}]"),
    ("internal/api/orders_client.go", "\treturn []Order{{ID: 1, Name: \"Latte\"}}, nil"),
    ("lib/di.dart", "  getIt.registerSingleton<OrdersRepository>(InMemoryOrdersRepository());"),
    ("app/main.py", "repo = InMemoryOrderRepository()"),
    ("lib/data/orders_api.dart", "  // TODO: replace with the real API call"),
    ("app/services/orders.py", "    # hardcoded for now until the backend exists"),
])
def test_rejects_stand_ins_below_the_screen(repo, rel, line):
    # Arrange
    _write(repo, rel, f"{line}\n")
    # Act
    result = _run(repo)
    # Assert
    assert result.returncode == 1, result.stdout
    assert f"{rel}:1" in result.stdout


@pytest.mark.parametrize("rel,line", [
    ("lib/data/orders_repository.dart", "    return [];"),
    ("lib/data/orders_repository.dart", "    return (json as List).map(Order.fromJson).toList();"),
    ("app/repositories/orders.py", "    return [Order(**row) for row in rows]"),
    ("lib/ui/orders_page.dart", "    return [Text(order.name), Text(order.price)];"),
    ("tests/test_orders.py", "repo = InMemoryOrderRepository()  # mock, John Doe"),
    ("app/conftest.py", "repo = InMemoryOrderRepository()"),
    ("internal/api/orders_client_test.go", "\treturn []Order{{ID: 1}}, nil"),
])
def test_allows_real_data_layers_and_test_doubles_in_tests(repo, rel, line):
    # Arrange
    _write(repo, rel, f"{line}\n")
    # Act
    result = _run(repo)
    # Assert
    assert result.returncode == 0, result.stdout
