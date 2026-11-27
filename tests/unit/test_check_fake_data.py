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


# A record built from values read at run time (Firestore, a request, a row) is real data.
@pytest.mark.parametrize("rel,line", [
    ("app/services/clients.py", '        return {"id": doc.id, "missing": True}'),
    ("app/services/clients.py", '    return {"id": client_id, "missing": True}  # not in Firestore'),
    ("app/api/reviews.py", "    return [{'id': snap.id, **snap.to_dict()}]"),
    ("lib/data/clients_repository.dart", "    return {'id': doc.id, 'missing': true};"),
    ("internal/api/clients_client.go", "\treturn []Client{{ID: id, Missing: true}}, nil"),
])
def test_allows_records_built_from_runtime_values(repo, rel, line):
    # Arrange
    _write(repo, rel, f"{line}\n")
    # Act
    result = _run(repo)
    # Assert
    assert result.returncode == 0, result.stdout


@pytest.mark.parametrize("line", [
    '    return {"id": "c-1", "missing": True}',
    "    return [{'id': 1, 'active': False, 'note': None}]  # doc.id later",
])
def test_rejects_records_made_only_of_literals(repo, line):
    # Arrange
    _write(repo, "app/services/clients.py", f"{line}\n")
    # Act
    result = _run(repo)
    # Assert
    assert result.returncode == 1, result.stdout


def _conflicted_merge(repo, incoming):
    """Starts a merge of a branch that adds `incoming` to app/services/clients.py, left with a conflict."""
    _write(repo, "app/notes.txt", "base\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "notes")
    _git(repo, "checkout", "-qb", "other")
    _write(repo, "app/services/clients.py", incoming)
    _write(repo, "app/notes.txt", "theirs\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "other")
    _git(repo, "checkout", "-q", "-")
    _write(repo, "app/notes.txt", "ours\n")
    _git(repo, "commit", "-qam", "ours")
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t.co", "merge", "other"], cwd=repo,
                   capture_output=True)


def test_ignores_lines_a_merge_brings_in_unchanged(repo):
    # Arrange
    _conflicted_merge(repo, "def get():\n    return [{'id': 1, 'name': 'Latte'}]\n")
    # Act
    result = _run(repo)
    # Assert
    assert result.returncode == 0, result.stdout


def test_still_checks_lines_added_during_a_merge(repo):
    # Arrange
    _conflicted_merge(repo, "def get():\n    return rows\n")
    _write(repo, "app/services/clients.py", "def get():\n    return [{'id': 1, 'name': 'Latte'}]\n")
    # Act
    result = _run(repo)
    # Assert
    assert result.returncode == 1, result.stdout
    assert "app/services/clients.py:2" in result.stdout


def test_allows_records_holding_call_results(repo):
    # Arrange
    _write(repo, "app/services/clients.py", '    return {"id": new_id(), "missing": True}\n')
    # Act
    result = _run(repo)
    # Assert
    assert result.returncode == 0, result.stdout


# C-02: a literal is a fallback or status response when its function reads a real source.
@pytest.mark.parametrize("rel,text", [
    ("app/services/clients.py",
     "def get_client(db, client_id):\n"
     "    snap = db.collection('clients').document(client_id).get()\n"
     "    if not snap.exists:\n"
     "        return {'error': 'not found', 'missing': True}\n"
     "    return snap.to_dict()\n"),
    ("src/api/orders.ts",
     "export async function loadOrders(userId: string) {\n"
     "  const res = await fetch(`/api/orders/${userId}`);\n"
     "  if (!res.ok) {\n"
     "    return [{ status: 'error' }];\n"
     "  }\n"
     "  return res.json();\n"
     "}\n"),
    ("lib/data/profile_repository.dart",
     "  Future<Map<String, dynamic>> profile(String id) async {\n"
     "    final doc = await _firestore.collection('profiles').doc(id).get();\n"
     "    if (!doc.exists) return {'missing': true};\n"
     "    return doc.data()!;\n"
     "  }\n"),
    ("internal/api/users_client.go",
     "func (c *Client) Users() ([]User, error) {\n"
     "\trows, err := c.db.Query(\"SELECT id FROM users\")\n"
     "\tif err != nil {\n"
     "\t\treturn []User{{ID: 0}}, err\n"
     "\t}\n"
     "\treturn scan(rows), nil\n"
     "}\n"),
])
def test_allows_literal_fallbacks_in_functions_that_read_a_real_source(repo, rel, text):
    # Arrange
    _write(repo, rel, text)
    # Act
    result = _run(repo)
    # Assert
    assert result.returncode == 0, result.stdout


def test_rejects_a_literal_in_a_function_that_reads_nothing_even_next_to_a_real_one(repo):
    # Arrange
    _write(repo, "app/services/clients.py",
           "def real(db):\n"
           "    return db.collection('clients').get()\n"
           "\n"
           "def invented():\n"
           "    return [{'id': 1, 'name': 'Latte'}]\n")
    # Act
    result = _run(repo)
    # Assert
    assert result.returncode == 1, result.stdout
    assert "app/services/clients.py:5" in result.stdout


def _cherry_pick_with_conflict(repo, incoming):
    _write(repo, "app/notes.txt", "base\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "notes")
    _git(repo, "checkout", "-qb", "other")
    _write(repo, "app/services/clients.py", incoming)
    _write(repo, "app/notes.txt", "theirs\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "other")
    _git(repo, "checkout", "-q", "-")
    _write(repo, "app/notes.txt", "ours\n")
    _git(repo, "commit", "-qam", "ours")
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t.co", "cherry-pick", "other"], cwd=repo,
                   capture_output=True)


def test_ignores_lines_a_cherry_pick_brings_in_unchanged(repo):
    # Arrange
    _cherry_pick_with_conflict(repo, "def get():\n    return [{'id': 1, 'name': 'Latte'}]\n")
    # Act
    result = _run(repo)
    # Assert
    assert result.returncode == 0, result.stdout


def test_a_source_named_only_in_the_signature_is_not_a_read(repo):
    # Arrange
    _write(repo, "app/services/clients.py",
           "def invented(db, session):\n"
           "    return [{'id': 1, 'name': 'Latte'}]\n")
    # Act
    result = _run(repo)
    # Assert
    assert result.returncode == 1, result.stdout


# C-03: false-positive families seen in real blocks (transcript replay, 2026-11).
@pytest.mark.parametrize("rel,line", [
    ("agent/scripts/export_surfaces.py", "flow = SellingFlow(FakeJev(), FakeWriter())"),
    ("backend/src/scripts/fake-cloudbeds.ts", "export function startFakeCloudbeds(options: FakeOptions) {"),
    ("scripts/seed_preview.py", "users = mock_users()"),
    ("mobile/lib/ui/catalog/contract.g.dart", "  'name': 'John Doe',"),
    ("lib/models/order.freezed.dart", "  final String sampleData;"),
    ("app/proto/orders_pb2.py", "FAKE_DESCRIPTOR = 1"),
    ("src/generated/api.ts", "export const mockServer = 1;"),
])
def test_ignores_dev_scripts_and_generated_code(repo, rel, line):
    # Arrange
    _write(repo, rel, f"{line}\n")
    # Act
    result = _run(repo)
    # Assert
    assert result.returncode == 0, result.stdout


@pytest.mark.parametrize("rel,text", [
    ("app/app_utils/services.py",
     "from google.adk.sessions.in_memory_session_service import InMemorySessionService\n"
     "def sessions():\n"
     "    return InMemorySessionService()\n"),
    ("app/fast_api_app.py",
     "from a2a.server.tasks import InMemoryTaskStore\n"
     "task_store = InMemoryTaskStore()\n"),
    ("src/server.ts",
     "import { InMemoryCache } from '@apollo/client';\n"
     "const cache = new InMemoryCache();\n"),
])
def test_allows_in_memory_classes_from_libraries(repo, rel, text):
    # Arrange
    _write(repo, rel, text)
    # Act
    result = _run(repo)
    # Assert
    assert result.returncode == 0, result.stdout


@pytest.mark.parametrize("rel,text", [
    ("app/main.py", "from app.repositories.orders import InMemoryOrderRepository\nrepo = InMemoryOrderRepository()\n"),
    ("src/main.ts", "import { InMemoryOrdersStore } from './orders';\nconst repo = new InMemoryOrdersStore();\n"),
    ("src/main.ts", "import { InMemoryOrdersStore } from '@/data/orders';\nconst repo = new InMemoryOrdersStore();\n"),
])
def test_rejects_in_memory_classes_from_the_project(repo, rel, text):
    # Arrange
    _write(repo, "app/repositories/orders.py", "class Placeholder:\n    pass\n")
    _write(repo, rel, text)
    # Act
    result = _run(repo)
    # Assert
    assert result.returncode == 1, result.stdout


@pytest.mark.parametrize("line", [
    "/** Runtime client: base URL overridable (local fake server in scripts/). */",
    "# Tests swap this for a mock client.",
    "    // demo-data: approved for the preview build",
])
def test_comments_that_only_mention_fakes_pass(repo, line):
    # Arrange
    _write(repo, "src/infrastructure/pms/cloudbeds.client.ts", f"{line}\n")
    # Act
    result = _run(repo)
    # Assert
    assert result.returncode == 0, result.stdout


def test_a_comment_that_leaves_the_real_source_for_later_still_fails(repo):
    # Arrange
    _write(repo, "src/api/orders.ts", "// hardcoded for now, connect to the real api later\n")
    # Act
    result = _run(repo)
    # Assert
    assert result.returncode == 1, result.stdout


@pytest.mark.parametrize("rel", ["app/tools/orders.py", "bin/server.py"])
def test_agent_tools_and_server_entry_points_are_still_scanned(repo, rel):
    # Arrange
    _write(repo, rel, "def list_orders():\n    return mock_orders()\n")
    # Act
    result = _run(repo)
    # Assert
    assert result.returncode == 1, result.stdout


def test_in_memory_helpers_that_hold_no_data_pass(repo):
    # Arrange
    _write(repo, "src/common/listing/list-query.ts", "export interface InMemoryAccessors<T> {\n")
    # Act
    result = _run(repo)
    # Assert
    assert result.returncode == 0, result.stdout


@pytest.mark.parametrize("rel,line", [
    ("lib/ui/providers/repository_providers.dart",
     "  throw UnimplementedError('Override at app bootstrap, or with a fake in tests.');"),
    ("content/courses/guia.py", '    "steps": ["Implementa get_rate (mock o API real) y calculator"],'),
    ("content/courses/s4.py", '    ["`InMemorySessionService` / `InMemoryRunner`", "Por defecto todo vive en memoria"],'),
    ("public/js/vendor.min.js", "!function(t){var mockData=1;Math.random()}(this);"),
    ("src/js/shuffle.js", "    const j = Math.floor(Math.random() * (i + 1));"),
    ("functions/index.js", "  pass += chars.charAt(Math.floor(Math.random() * chars.length));"),
    ("functions/index.js", "  const proofPath = `payments/${id}/${Date.now()}-${Math.random().toString(36).slice(2)}`;"),
])
def test_text_minified_code_and_random_indexes_pass(repo, rel, line):
    # Arrange
    _write(repo, rel, f"{line}\n")
    # Act
    result = _run(repo)
    # Assert
    assert result.returncode == 0, result.stdout


def test_a_minified_line_is_skipped(repo):
    # Arrange
    _write(repo, "public/js/ui.js", "var a=1;" * 200 + "var mockUsers=[];\n")
    # Act
    result = _run(repo)
    # Assert
    assert result.returncode == 0, result.stdout


def test_an_in_memory_library_class_in_dart_passes_and_a_local_one_fails(repo):
    # Arrange
    _write(repo, "lib/data/agent_factory.dart",
           "import 'package:adk/adk.dart';\n"
           "final sessions = InMemorySessionService();\n")
    _write(repo, "lib/data/local_repo.dart", "class InMemoryOrdersRepository {}\n")
    _write(repo, "lib/di.dart", "import 'package:adk/adk.dart';\nfinal repo = InMemoryOrdersRepository();\n")
    # Act
    result = _run(repo)
    # Assert
    assert result.returncode == 1, result.stdout
    assert "lib/data/agent_factory.dart" not in result.stdout
    assert "lib/di.dart:2" in result.stdout


def test_a_random_displayed_value_still_fails(repo):
    # Arrange
    _write(repo, "src/pages/Stats.tsx", "const revenue = Math.round(Math.random() * 1000);\n")
    # Act
    result = _run(repo)
    # Assert
    assert result.returncode == 1, result.stdout
