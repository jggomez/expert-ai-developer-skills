# Building the desktop app

Apps are built on their own system, unsigned. `build_desktop.py` freezes the app and runs its self-test, so a bundle with a
missing module fails here and not on someone's machine.

```bash
uv sync --extra app
uv pip install pyinstaller
uv run --no-sync python packaging/build_desktop.py   # dist/agent-meter-<version>-<system>-<arch>.dmg or .exe
```

**Release:** set `version` in `pyproject.toml`, push the tag `agent-meter-v<version>`, then review and publish the draft that
the `agent-meter desktop` workflow creates. The app's update check only sees published releases.
