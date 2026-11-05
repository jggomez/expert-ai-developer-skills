"""Dependencies point inwards: entrypoints -> adapters -> application -> domain."""

import ast
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src"
PACKAGE = SRC / "pr_reviewer"
ALLOWED_THIRD_PARTY = {
    "domain": {"pydantic"},
    "application": set(),
    "adapters/git": set(),
    "adapters/filesystem": set(),
    "adapters/github": {"httpx"},
    "adapters/providers": {"pydantic", "google", "anthropic"},
    "entrypoints": set(),
}
FORBIDDEN_LAYERS = {
    "domain": ("application", "adapters", "entrypoints"),
    "application": ("adapters", "entrypoints"),
    "adapters": ("entrypoints",),
}


def imports(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def modules(folder: str) -> list[Path]:
    return sorted((PACKAGE / folder).rglob("*.py"))


@pytest.mark.parametrize("layer", FORBIDDEN_LAYERS)
def test_layers_do_not_import_outer_layers(layer: str):
    # Arrange
    forbidden = tuple(f"pr_reviewer.{outer}" for outer in FORBIDDEN_LAYERS[layer])

    # Act
    offenders = {str(p.relative_to(SRC)): name for p in modules(layer) for name in imports(p) if name.startswith(forbidden)}

    # Assert
    assert offenders == {}


@pytest.mark.parametrize("folder", ALLOWED_THIRD_PARTY)
def test_third_party_libraries_stay_in_their_layer(folder: str):
    # Arrange
    allowed = {"pr_reviewer", "__future__"} | ALLOWED_THIRD_PARTY[folder] | set(sys.stdlib_module_names)

    # Act
    offenders = {str(p.relative_to(SRC)): name for p in modules(folder) for name in imports(p) if name.split(".")[0] not in allowed}

    # Assert
    assert offenders == {}


def test_every_source_module_belongs_to_a_layer():
    # Act
    outside = [p for p in PACKAGE.glob("*.py") if p.name != "__init__.py"]

    # Assert
    assert outside == []


def test_only_the_composition_root_chooses_adapters_for_the_use_cases():
    # Act
    offenders = [p.name for p in modules("application") if "providers" in str(imports(p))]

    # Assert
    assert offenders == []
