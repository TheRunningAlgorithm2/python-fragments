import sys
from pathlib import Path

import pytest

pytest.importorskip("black")

from fragments import cli  # noqa: E402

MESSY = "x   = {'a':1}\ny = <><b>hi</b></>\n"
CLEAN = 'x = {"a": 1}\ny = <><b>hi</b></>\n'


def run(monkeypatch: pytest.MonkeyPatch, *arguments: str) -> int:
    monkeypatch.setattr(sys, "argv", ["fragments", "format", *arguments])
    try:
        cli.main()
    except SystemExit as error:
        return int(error.code or 0)
    return 0


def test_writes_multiple_files_in_place(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    first, second = tmp_path / "a.py", tmp_path / "b.py"
    first.write_text(MESSY)
    second.write_text(MESSY)
    assert run(monkeypatch, str(first), str(second)) == 0
    assert first.read_text() == second.read_text() == CLEAN


def test_directory_is_expanded_and_hidden_directories_skipped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    (tmp_path / "pkg").mkdir()
    (tmp_path / ".venv").mkdir()
    (tmp_path / "pkg" / "a.py").write_text(MESSY)
    (tmp_path / ".venv" / "b.py").write_text(MESSY)
    assert run(monkeypatch, str(tmp_path)) == 0
    assert (tmp_path / "pkg" / "a.py").read_text() == CLEAN
    assert (tmp_path / ".venv" / "b.py").read_text() == MESSY


def test_check_fails_without_writing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    path = tmp_path / "a.py"
    path.write_text(MESSY)
    assert run(monkeypatch, "--check", str(path)) == 1
    assert path.read_text() == MESSY


def test_check_passes_when_already_formatted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    path = tmp_path / "a.py"
    path.write_text(CLEAN)
    assert run(monkeypatch, "--check", str(path)) == 0


def test_parse_error_is_reported_and_other_files_still_formatted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]):
    broken, fine = tmp_path / "broken.py", tmp_path / "fine.py"
    broken.write_text("x = 1\ny = <><p class='row'>hi</p></>\n")
    fine.write_text(MESSY)
    assert run(monkeypatch, str(broken), str(fine)) == 1
    assert f"{broken}:2:" in capsys.readouterr().err
    assert fine.read_text() == CLEAN


def test_no_files_is_an_error(monkeypatch: pytest.MonkeyPatch):
    assert run(monkeypatch) == 2


def test_dry_run_prints_without_writing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]):
    path = tmp_path / "a.py"
    path.write_text(MESSY)
    assert run(monkeypatch, "--dry-run", str(path)) == 0
    assert capsys.readouterr().out == CLEAN
    assert path.read_text() == MESSY
