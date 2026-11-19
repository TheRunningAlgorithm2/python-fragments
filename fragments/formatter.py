from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from re import Pattern
from typing import cast

import black
import click
from black.files import find_project_root
from black.mode import Preview, TargetVersion
from black.report import Report

from fragments import grammar
from fragments.ast_nodes import ASTFragment
from fragments.source import Source


class ConfigurationError(Exception):
    """The Black configuration that applies to the requested paths is invalid."""


@dataclass(frozen=True)
class Configuration:
    """The Black mode and the files to format, resolved exactly as the `black` command resolves them."""

    mode: black.Mode
    sources: list[Path]


def load_configuration(paths: Sequence[Path]) -> Configuration:
    """Resolve the Black configuration and the Python files to format for `paths`.

    Black's own command line parser is run without formatting anything, so `[tool.black]` in the nearest
    pyproject.toml is found, validated and applied the same way the `black` command does it, including
    `exclude`, `extend-exclude`, `force-exclude`, `.gitignore` and target versions inferred from
    `requires-python`. Directories are expanded into the files Black would format, keeping only `.py` files
    because notebooks and stubs are not supported.

    Raises:
        ConfigurationError: If a pyproject.toml cannot be read or its `[tool.black]` table is invalid.
    """
    try:
        # Black's parser consumes the list it is given, so it always gets a fresh one.
        context = black.main.make_context("black", [str(path) for path in paths])
    except click.ClickException as error:
        raise ConfigurationError(error.format_message()) from error
    except ValueError as error:  # invalid TOML found while searching upwards for the project root
        raise ConfigurationError(f"could not read pyproject.toml: {error}") from error

    parameters = context.params
    sources = cast(tuple[str, ...], parameters["src"])
    root, _ = find_project_root(sources)
    found = black.get_sources(
        root=root,
        src=sources,
        quiet=True,
        verbose=False,
        include=cast(Pattern[str], parameters["include"]),
        exclude=cast(Pattern[str] | None, parameters["exclude"]),
        extend_exclude=cast(Pattern[str] | None, parameters["extend_exclude"]),
        force_exclude=cast(Pattern[str] | None, parameters["force_exclude"]),
        report=Report(),
        stdin_filename=None,
    )
    mode = black.Mode(
        target_versions=set(cast(list[TargetVersion], parameters["target_version"])),
        line_length=cast(int, parameters["line_length"]),
        string_normalization=not cast(bool, parameters["skip_string_normalization"]),
        magic_trailing_comma=not cast(bool, parameters["skip_magic_trailing_comma"]),
        preview=cast(bool, parameters["preview"]),
        unstable=cast(bool, parameters["unstable"]),
        enabled_features=set(cast(list[Preview], parameters["enable_unstable_feature"])),
    )
    return Configuration(mode=mode, sources=sorted(path for path in found if path.suffix == ".py"))


def format_source(source_string: str, mode: black.Mode | None = None) -> str:
    """Format the Python surrounding fragments, leaving the fragments untouched.

    Black cannot parse fragment syntax, so each top-level fragment is swapped for a placeholder identifier,
    the resulting plain Python is formatted with Black, and the original fragment text is then swapped back
    in verbatim. Anything inside `<>...</>`, including `{{ }}` interpolations, is never modified.

    Args:
        source_string: The full contents of a Python file that may contain fragments.

    Returns:
        The source with the surrounding Python formatted by Black and every
        fragment byte-for-byte identical to the input.

    Raises:
        grammar.ParsingError: If the source is not valid fragments syntax.
        black.InvalidInput: If the Python around the fragments is not valid.
    """
    _, module = grammar.expect_module(Source.from_string(source_string))

    # Choose a placeholder prefix that does not already appear in the source, so a placeholder can never be
    # confused with real code when substituting back.
    prefix = "__fragment"
    while prefix in source_string:
        prefix = "_" + prefix

    # Rebuild the file as plain Python, recording each fragment's original text (sliced from the source, so
    # it is preserved byte for byte) by placeholder name.
    fragments: dict[str, str] = {}
    parts: list[str] = []
    for child in module.children:
        if not isinstance(child, ASTFragment):
            parts.append(child.content)
            continue
        placeholder = f"{prefix}_{len(fragments)}__"
        fragments[placeholder] = source_string[child.source_start : child.source_end]
        parts.append(placeholder)

    # Format the plain Python, then put the untouched fragments back in place.
    formatted = black.format_str("".join(parts), mode=mode or black.Mode())
    for placeholder, original in fragments.items():
        formatted = formatted.replace(placeholder, original)
    return formatted
