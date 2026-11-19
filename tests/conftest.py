from importlib.util import find_spec
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def no_user_black_config(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stop Black falling back to the developer's own `~/.config/black` when a test project has no pyproject.toml."""
    if find_spec("black") is None:
        return
    missing: Path = tmp_path_factory.mktemp("home") / "black"
    monkeypatch.setattr("black.files.find_user_pyproject_toml", lambda: missing)
