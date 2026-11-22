"""Every workflow has YAML frontmatter with a description the portal and slash-command pickers can read."""
import glob
import os

import pytest
import yaml

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
WORKFLOWS = sorted(glob.glob(os.path.join(REPO_ROOT, "workflows", "*-workflow.md")))


@pytest.mark.parametrize("path", WORKFLOWS, ids=os.path.basename)
def test_workflow_has_parseable_description(path):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    assert text.startswith("---\n"), "missing frontmatter"
    meta = yaml.safe_load(text.split("---", 2)[1])
    assert isinstance(meta.get("description"), str) and meta["description"].startswith("Use ")
