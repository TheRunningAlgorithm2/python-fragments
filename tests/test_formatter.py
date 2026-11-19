import asyncio
import sys
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

pytest.importorskip("black")

import black  # noqa: E402
from black.mode import TargetVersion  # noqa: E402

import fragments  # noqa: E402
from fragments.formatter import ConfigurationError, format_source, load_configuration  # noqa: E402
from fragments.transpiler import transpile  # noqa: E402

if TYPE_CHECKING:
    from lsprotocol import types

UNFORMATTED = """import os
def page(title,items):
    x   = {'a':1}
    return <>
        <h1>{{title}}</h1>
          <ul><li for={{i in items}}>{{i}}</li></ul>
    </>
y = foo( <><b>hi</b></>,   2)
"""


def write_config(directory: Path, body: str) -> Path:
    """Write a pyproject.toml into `directory` and return the path of a module that it governs."""
    (directory / "pyproject.toml").write_text(body)
    return directory / "module.py"


def hide_black(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make `import black` fail, and force `fragments.formatter` to be imported again so that it hits the failure."""
    monkeypatch.setitem(sys.modules, "black", None)
    monkeypatch.delitem(sys.modules, "fragments.formatter", raising=False)
    monkeypatch.delattr(fragments, "formatter", raising=False)


def test_python_is_formatted():
    formatted = format_source(UNFORMATTED)
    assert 'x = {"a": 1}' in formatted
    assert "y = foo(<><b>hi</b></>, 2)" in formatted


def test_fragments_are_untouched():
    formatted = format_source(UNFORMATTED)
    assert "<h1>{{title}}</h1>\n          <ul><li for={{i in items}}>{{i}}</li></ul>" in formatted


def test_idempotent():
    once = format_source(UNFORMATTED)
    assert format_source(once) == once


def test_transpiled_output_unchanged():
    normalize = lambda source: black.format_str(transpile(source), mode=black.Mode())
    assert normalize(format_source(UNFORMATTED)) == normalize(UNFORMATTED)


def test_placeholder_collision():
    source = "__fragment_0__ = <><b>hi</b></>\n"
    assert format_source(source) == source


def test_format_source_applies_mode() -> None:
    source = "x = {'a': 1}\ny = <><b>hi</b></>\n"
    assert format_source(source, black.Mode(string_normalization=False)) == source


def test_format_source_defaults_when_mode_is_none() -> None:
    assert format_source(UNFORMATTED, None) == format_source(UNFORMATTED, black.Mode())


def load_mode(path: Path) -> black.Mode:
    """Create `path` so Black's parser accepts it, then return the mode that applies to it."""
    path.touch()
    return load_configuration([path]).mode


def test_load_configuration_reads_tool_black(tmp_path: Path) -> None:
    path = write_config(
        tmp_path,
        """[tool.black]
line-length = 60
target-version = ["py311", "py312"]
skip-string-normalization = true
skip-magic-trailing-comma = true
preview = true
""",
    )
    mode = load_mode(path)
    assert mode.line_length == 60
    assert mode.target_versions == {TargetVersion.PY311, TargetVersion.PY312}
    assert mode.string_normalization is False
    assert mode.magic_trailing_comma is False
    assert mode.preview is True


def test_load_configuration_infers_target_versions_from_requires_python(tmp_path: Path) -> None:
    path = write_config(
        tmp_path,
        """[project]
name = "example"
requires-python = ">=3.13"

[tool.black]
""",
    )
    target_versions = load_mode(path).target_versions
    assert TargetVersion.PY313 in target_versions
    assert TargetVersion.PY312 not in target_versions


def test_load_configuration_defaults_without_pyproject(tmp_path: Path) -> None:
    assert load_mode(tmp_path / "module.py") == black.Mode()


def test_load_configuration_defaults_without_tool_black_table(tmp_path: Path) -> None:
    path = write_config(tmp_path, "[project]\nname = 'example'\n")
    assert load_mode(path) == black.Mode()


def test_load_configuration_uses_nearest_pyproject(tmp_path: Path) -> None:
    write_config(tmp_path, "[tool.black]\nline-length = 100\n")
    nested = tmp_path / "package"
    nested.mkdir()
    path = write_config(nested, "[tool.black]\nline-length = 50\n")
    assert load_mode(path).line_length == 50


@pytest.mark.parametrize(
    ("body", "option"),
    [
        ('target-version = ["py99"]', "target-version"),
        ('target-version = "py311"', "target-version"),
        ('line-length = "wide"', "line-length"),
        ('enable-unstable-feature = ["not_a_feature"]', "enable-unstable-feature"),
    ],
)
def test_load_configuration_rejects_invalid_values(tmp_path: Path, body: str, option: str) -> None:
    path = write_config(tmp_path, f"[tool.black]\n{body}\n")
    with pytest.raises(ConfigurationError, match=option):
        load_mode(path)


def test_load_configuration_rejects_invalid_toml(tmp_path: Path) -> None:
    path = write_config(tmp_path, "[tool.black\n")
    with pytest.raises(ConfigurationError):
        load_mode(path)


def test_load_configuration_rejects_missing_paths(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="does not exist"):
        load_configuration([tmp_path / "missing.py"])


def make_project(directory: Path, config: str, files: list[str]) -> None:
    """Create a project root with `config` as its `[tool.black]` table and an empty file at each of `files`."""
    (directory / "pyproject.toml").write_text(f"[tool.black]\n{config}\n")
    for name in files:
        file = directory / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.touch()


def source_names(directory: Path) -> list[str]:
    return [str(path.relative_to(directory)) for path in load_configuration([directory]).sources]


def test_sources_skip_default_excludes(tmp_path: Path) -> None:
    make_project(tmp_path, "", ["package/a.py", ".venv/b.py", "build/c.py"])
    assert source_names(tmp_path) == ["package/a.py"]


def test_sources_honour_extend_exclude(tmp_path: Path) -> None:
    make_project(tmp_path, "extend-exclude = '^/generated/'", ["package/a.py", "generated/b.py"])
    assert source_names(tmp_path) == ["package/a.py"]


def test_sources_honour_gitignore(tmp_path: Path) -> None:
    make_project(tmp_path, "", ["package/a.py", "scratch/b.py"])
    (tmp_path / ".gitignore").write_text("scratch/\n")
    assert source_names(tmp_path) == ["package/a.py"]


def test_sources_only_include_python_files(tmp_path: Path) -> None:
    make_project(tmp_path, "", ["a.py", "b.pyi", "c.ipynb"])
    assert source_names(tmp_path) == ["a.py"]


def test_explicit_file_is_kept_despite_extend_exclude(tmp_path: Path) -> None:
    make_project(tmp_path, "extend-exclude = '^/generated/'", ["generated/a.py"])
    assert load_configuration([tmp_path / "generated" / "a.py"]).sources != []


def test_explicit_file_is_dropped_when_force_excluded(tmp_path: Path) -> None:
    make_project(tmp_path, "force-exclude = '^/generated/'", ["generated/a.py"])
    assert load_configuration([tmp_path / "generated" / "a.py"]).sources == []


def test_formatting_edits_replace_whole_document():
    from fragments.lsp.client_message_handlers.formatting import formatting_edits

    (edit,) = formatting_edits(UNFORMATTED)
    assert edit.new_text == format_source(UNFORMATTED)
    assert (edit.range.start.line, edit.range.start.character) == (0, 0)
    assert (edit.range.end.line, edit.range.end.character) == (
        UNFORMATTED.count("\n"),
        0,
    )


def test_formatting_edits_empty_when_already_formatted():
    from fragments.lsp.client_message_handlers.formatting import formatting_edits

    assert formatting_edits(format_source(UNFORMATTED)) == []


def test_formatting_edits_empty_when_python_is_invalid():
    from fragments.lsp.client_message_handlers.formatting import formatting_edits

    assert formatting_edits("def broken(:\n") == []


def test_formatting_edits_applies_project_config(tmp_path: Path) -> None:
    from fragments.lsp.client_message_handlers.formatting import formatting_edits

    path = write_config(tmp_path, "[tool.black]\nskip-string-normalization = true\n")
    path.touch()
    (edit,) = formatting_edits("x = {'a':1}\n", path)
    assert edit.new_text == "x = {'a': 1}\n"


def test_formatting_edits_empty_when_force_excluded(tmp_path: Path) -> None:
    from fragments.lsp.client_message_handlers.formatting import formatting_edits

    make_project(tmp_path, "force-exclude = '^/generated/'", ["generated/a.py"])
    assert formatting_edits("x = {'a':1}\n", tmp_path / "generated" / "a.py") == []


def test_formatting_edits_uses_defaults_without_path() -> None:
    from fragments.lsp.client_message_handlers.formatting import formatting_edits

    (edit,) = formatting_edits("x = {'a':1}\n", None)
    assert edit.new_text == 'x = {"a": 1}\n'


def test_formatting_edits_raises_on_invalid_config(tmp_path: Path) -> None:
    """A broken config must surface as an error, not be swallowed by the `except ValueError` for syntax errors."""
    from fragments.lsp.client_message_handlers.formatting import formatting_edits

    path = write_config(tmp_path, '[tool.black]\ntarget-version = ["py99"]\n')
    path.touch()
    with pytest.raises(ConfigurationError, match="target-version"):
        formatting_edits("x = 1\n", path)


def test_formatting_edits_reports_missing_black(monkeypatch: pytest.MonkeyPatch) -> None:
    from fragments.lsp.client_message_handlers.formatting import formatting_edits

    hide_black(monkeypatch)
    with pytest.raises(RuntimeError, match=r"python-fragments\[format\]"):
        formatting_edits("x = 1\n", None)


@pytest.mark.parametrize(
    ("uri", "expected"),
    [
        ("file:///home/user/project/app.py", Path("/home/user/project/app.py")),
        ("file:///home/user/my%20project/app.py", Path("/home/user/my project/app.py")),
        ("untitled:Untitled-1", None),
    ],
)
def test_uri_to_path(uri: str, expected: Path | None) -> None:
    from fragments.lsp.client_message_handlers.formatting import _uri_to_path

    assert _uri_to_path(uri) == expected


def run_formatting_handler(
    monkeypatch: pytest.MonkeyPatch,
    uri: str,
    replacement: Callable[[str, Path | None], list["types.TextEdit"]],
) -> list["types.ResponseErrorMessage | types.DocumentFormattingResponse"]:
    """Send a formatting request for `uri` through the handler, with `formatting_edits` replaced, and return the responses."""
    from lsprotocol import types

    from fragments.lsp import based_proxy
    from fragments.lsp.client_message_handlers import formatting
    from fragments.lsp.file_state import FileState

    class RecordingProxy:
        def __init__(self) -> None:
            self.responses: list[types.ResponseErrorMessage | types.DocumentFormattingResponse] = []

        def respond(
            self,
            request_id: int | str,
            response: types.ResponseErrorMessage | types.DocumentFormattingResponse,
        ) -> None:
            self.responses.append(response)

    proxy = RecordingProxy()
    monkeypatch.setattr(based_proxy, "_PROXY", proxy)
    monkeypatch.setitem(based_proxy.FILE_STATES, uri, FileState(UNFORMATTED))
    monkeypatch.setattr(formatting, "formatting_edits", replacement)

    request = types.DocumentFormattingRequest(
        id=7,
        params=types.DocumentFormattingParams(
            text_document=types.TextDocumentIdentifier(uri=uri),
            options=types.FormattingOptions(tab_size=4, insert_spaces=True),
        ),
    )
    asyncio.run(formatting.formatting(request))
    return proxy.responses


def test_formatting_handler_responds_with_error_when_formatting_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from lsprotocol import types

    def fail(original: str, path: Path | None = None) -> list[types.TextEdit]:
        raise RuntimeError("Formatting requires black")

    (response,) = run_formatting_handler(monkeypatch, "file:///t.py", fail)
    assert isinstance(response, types.ResponseErrorMessage)
    assert response.error is not None
    assert "black" in response.error.message


def test_formatting_handler_passes_file_path(monkeypatch: pytest.MonkeyPatch) -> None:
    from lsprotocol import types

    received: list[Path | None] = []

    def record(original: str, path: Path | None = None) -> list[types.TextEdit]:
        received.append(path)
        return []

    run_formatting_handler(monkeypatch, "file:///project/app.py", record)
    assert received == [Path("/project/app.py")]


def test_formatting_handler_passes_no_path_for_untitled_documents(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from lsprotocol import types

    received: list[Path | None] = []

    def record(original: str, path: Path | None = None) -> list[types.TextEdit]:
        received.append(path)
        return []

    run_formatting_handler(monkeypatch, "untitled:Untitled-1", record)
    assert received == [None]
