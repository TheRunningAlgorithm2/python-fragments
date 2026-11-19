import shlex
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from re import Pattern
from typing import cast

import black
import click
from black.files import find_project_root
from black.mode import Preview, TargetVersion
from black.output import diff as unified_diff
from black.report import Report

from fragments import grammar
from fragments.ast_nodes import ASTFragment
from fragments.source import Source


class ConfigurationError(Exception):
    """The Black configuration or arguments that apply to the requested paths are invalid."""


# Black options that change what the input is. Fragments cannot honour them, and ignoring them would silently
# produce output the user did not ask for, so they are rejected. Keyed by Black's parameter name.
UNSUPPORTED_OPTIONS: dict[str, str] = {
    "code": "--code",
    "pyi": "--pyi",
    "ipynb": "--ipynb",
    "python_cell_magics": "--python-cell-magics",
    "skip_source_first_line": "--skip-source-first-line",
    "line_ranges": "--line-ranges",
    "stdin_filename": "--stdin-filename",
}

# Options that make Black's parser print to stdout and exit. Stdout is the LSP channel in the language server,
# so these must never reach the parser from editor settings.
EXITING_OPTIONS = frozenset({"-h", "--help", "--version"})


@dataclass(frozen=True)
class Configuration:
    """The Black mode, output options and files to format, resolved exactly as the `black` command resolves them."""

    mode: black.Mode
    sources: list[Path]
    check: bool = False
    diff: bool = False
    quiet: bool = False


def split_black_arguments(text: str) -> list[str]:
    """Split a string of Black command line arguments.

    Raises:
        ConfigurationError: If the string cannot be split, for example because a quote is never closed.
    """
    try:
        return shlex.split(text)
    except ValueError as error:
        raise ConfigurationError(f"could not parse Black arguments {text!r}: {error}") from error


def load_configuration(paths: Sequence[Path], black_arguments: Sequence[str] = ()) -> Configuration:
    """Resolve the Black configuration and the Python files to format for `paths`.

    `black_arguments` are Black command line options, such as `["-l", "100"]`, applied on top of `[tool.black]`
    exactly as they would be by the `black` command. They must not contain paths or options that exit.

    Raises:
        ConfigurationError: If the arguments are invalid, or a pyproject.toml cannot be read or its
            `[tool.black]` table is invalid.
    """
    for argument in black_arguments:
        if argument in EXITING_OPTIONS:
            raise ConfigurationError(f"{argument} is not supported in Black arguments")
    arguments = [*black_arguments, "--", *(str(path) for path in paths)]
    configuration, sources = _parse(arguments)
    # The paths follow `--`, so any extra positional arguments came from `black_arguments` and are listed first.
    unexpected = sources[: len(sources) - len(paths)]
    if unexpected:
        raise ConfigurationError(f"Black arguments must not contain paths: {' '.join(unexpected)}")
    return configuration


def load_command_line_configuration(arguments: Sequence[str]) -> Configuration:
    """Resolve the configuration, where positional arguments are the paths.

    Black's own parser handles `-h/--help` and `--version` by printing and raising `click.exceptions.Exit`,
    which the caller is expected to turn into the process exit code.

    Raises:
        ConfigurationError: If the arguments or the configuration are invalid, or no paths are given.
    """
    configuration, sources = _parse(arguments)
    if not sources:
        raise ConfigurationError("no files given")
    return configuration


def _parse(arguments: Sequence[str]) -> tuple[Configuration, tuple[str, ...]]:
    """Run Black's own command line parser over `arguments` without formatting anything.

    Using Black's parser means `[tool.black]` in the nearest pyproject.toml is found, validated and merged with
    the arguments the same way the `black` command does it, including `exclude`, `extend-exclude`,
    `force-exclude`, `.gitignore` and target versions inferred from `requires-python`. Directories are
    expanded into the files Black would format, keeping only `.py` files because notebooks and stubs are not
    supported.

    Returns:
        The configuration, and the positional paths exactly as they were given.
    """
    try:
        context = black.main.make_context("black", list(arguments))
    except click.ClickException as error:
        raise ConfigurationError(error.format_message()) from error
    except ValueError as error:  # invalid TOML found while searching upwards for the project root
        raise ConfigurationError(f"could not read pyproject.toml: {error}") from error

    parameters = context.params
    for name, option in UNSUPPORTED_OPTIONS.items():
        if parameters[name]:
            raise ConfigurationError(f"{option} is not supported when formatting fragments")

    mode = black.Mode(
        target_versions=set(cast(list[TargetVersion], parameters["target_version"])),
        line_length=cast(int, parameters["line_length"]),
        string_normalization=not cast(bool, parameters["skip_string_normalization"]),
        magic_trailing_comma=not cast(bool, parameters["skip_magic_trailing_comma"]),
        preview=cast(bool, parameters["preview"]),
        unstable=cast(bool, parameters["unstable"]),
        enabled_features=set(cast(list[Preview], parameters["enable_unstable_feature"])),
    )
    check = cast(bool, parameters["check"])
    diff = cast(bool, parameters["diff"])
    quiet = cast(bool, parameters["quiet"])
    sources = cast(tuple[str, ...], parameters["src"])
    if not sources:
        configuration = Configuration(mode=mode, sources=[], check=check, diff=diff, quiet=quiet)
        return configuration, sources
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
    configuration = Configuration(
        mode=mode,
        sources=sorted(path for path in found if path.suffix == ".py"),
        check=check,
        diff=diff,
        quiet=quiet,
    )
    return configuration, sources


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


def diff(original: str, formatted: str, name: str) -> str:
    """Build the unified diff that `black --diff` prints for a file named `name`."""
    return unified_diff(original, formatted, f"{name}\t(original)", f"{name}\t(formatted)")
