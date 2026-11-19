import argparse
import sys
from pathlib import Path
from typing import cast

from fragments import grammar, transpiler
from fragments.source import Source


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser("fragments", description="Fragments transpilation CLI tool")
    command_parser = parser.add_subparsers(required=True)
    transpile_parser = command_parser.add_parser("transpile")
    transpile_parser.add_argument("--input", type=str, required=True)
    transpile_parser.set_defaults(func=transpile)
    ast_parser = command_parser.add_parser("ast")
    ast_parser.add_argument("--input", type=str, required=True)
    ast_parser.set_defaults(func=ast)
    black_parser = command_parser.add_parser(
        "black",
        add_help=False,
        help="Format the Python surrounding fragments with Black; accepts Black's command line options",
        description="Arguments are passed to Black's internal parser; run `fragments black --help` for its options.",
    )
    black_parser.set_defaults(func=black)
    arguments, remaining = parser.parse_known_args()
    if arguments.func is not black and remaining:
        parser.error(f"unrecognized arguments: {' '.join(remaining)}")
    arguments.black_arguments = remaining
    return arguments


def transpile(args: argparse.Namespace) -> None:
    """Transpile the specified file."""
    with open(args.input, "r") as f:
        source = f.read()
    print(transpiler.transpile(source))


def ast(args: argparse.Namespace) -> None:
    """Print the AST of the specified file."""
    with open(args.input, "r") as f:
        source_string = f.read()

    source = Source.from_string(source_string)
    _, module_ast = grammar.expect_module(source)
    module_ast.transpile()
    print(module_ast)


def _display(path: Path) -> Path:
    """Show a path relative to the working directory when it is inside it, as Black's output does."""
    if not path.is_absolute():
        return path
    try:
        return path.relative_to(Path.cwd())
    except ValueError:
        return path


def _line_and_column(source: str, offset: int) -> tuple[int, int]:
    """Convert a source offset into a 1-based line and column."""
    line = source.count("\n", 0, offset) + 1
    column = offset - (source.rfind("\n", 0, offset) + 1) + 1
    return line, column


def black(args: argparse.Namespace) -> None:
    """Format the Python surrounding fragments in the specified files with Black, leaving the fragments untouched."""
    try:
        import click

        from fragments import formatter
    except ModuleNotFoundError as error:
        if error.name not in ("black", "click"):
            raise
        print(
            "Formatting requires black: pip install python-fragments[black]",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        configuration = formatter.load_command_line_configuration(cast(list[str], args.black_arguments))
    except formatter.ConfigurationError as error:
        print(f"fragments black: {error}", file=sys.stderr)
        sys.exit(2)
    except click.exceptions.Exit as exit_request:  # --help or --version, already printed by Black's parser
        sys.exit(exit_request.exit_code)

    def report(message: str) -> None:
        if not configuration.quiet:
            print(message, file=sys.stderr)

    failed = False
    for source_path in configuration.sources:
        path = _display(source_path)
        source = source_path.read_text()
        try:
            formatted = formatter.format_source(source, configuration.mode)
        except grammar.ParsingError as error:
            line, column = _line_and_column(source, error.source_start)
            print(f"{path}:{line}:{column}: {error}", file=sys.stderr)
            failed = True
            continue
        except ValueError as error:  # black.InvalidInput: the Python around the fragments is invalid
            print(f"{path}: {error}", file=sys.stderr)
            failed = True
            continue

        if formatted == source:
            continue
        if configuration.diff:
            print(formatter.diff(source, formatted, str(path)), end="")
        if configuration.check or configuration.diff:
            report(f"would reformat {path}")
            failed = failed or configuration.check
            continue
        source_path.write_text(formatted)
        report(f"reformatted {path}")

    if failed:
        sys.exit(1)


def main():
    args = parse_args()
    assert hasattr(args, "func")
    args.func(args)


if __name__ == "__main__":
    main()
