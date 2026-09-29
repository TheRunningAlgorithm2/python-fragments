import argparse
import sys
from pathlib import Path

from fragments import formatter, grammar, transpiler
from fragments.source import Source


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        "fragments", description="Fragments transpilation CLI tool"
    )
    command_parser = parser.add_subparsers(required=True)
    transpile_parser = command_parser.add_parser("transpile")
    transpile_parser.add_argument("--input", type=str, required=True)
    transpile_parser.set_defaults(func=transpile)
    ast_parser = command_parser.add_parser("ast")
    ast_parser.add_argument("--input", type=str, required=True)
    ast_parser.set_defaults(func=ast)
    format_parser = command_parser.add_parser("format")
    format_parser.add_argument(
        "paths",
        nargs="*",
        help="Files or directories to format (directories are searched for *.py)",
    )
    format_parser.add_argument(
        "--input", action="append", default=[], help="Same as a positional path"
    )
    format_parser.add_argument(
        "--check",
        action="store_true",
        help="Don't write; exit 1 if any file would change",
    )
    format_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the formatted source without writing any files",
    )
    format_parser.set_defaults(func=format)
    return parser.parse_args()


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


def _expand_paths(paths: list[str]) -> list[Path]:
    """Expand directories into the Python files inside them, skipping hidden directories such as .venv."""
    expanded: list[Path] = []
    for path in map(Path, paths):
        if not path.is_dir():
            expanded.append(path)
            continue
        expanded.extend(
            candidate
            for candidate in sorted(path.rglob("*.py"))
            if not any(
                part.startswith(".") for part in candidate.relative_to(path).parts
            )
        )
    return expanded


def _line_and_column(source: str, offset: int) -> tuple[int, int]:
    """Convert a source offset into a 1-based line and column."""
    line = source.count("\n", 0, offset) + 1
    column = offset - (source.rfind("\n", 0, offset) + 1) + 1
    return line, column


def format(args: argparse.Namespace) -> None:
    """Format the Python surrounding fragments in the specified files, leaving the fragments untouched."""
    paths = _expand_paths(args.paths + args.input)
    if not paths:
        print("fragments format: no files given", file=sys.stderr)
        sys.exit(2)

    failed = False
    for path in paths:
        source = path.read_text()
        try:
            formatted = formatter.format_source(source)
        except grammar.ParsingError as error:
            line, column = _line_and_column(source, error.source_start)
            print(f"{path}:{line}:{column}: {error}", file=sys.stderr)
            failed = True
            continue
        except (
            ValueError
        ) as error:  # black.InvalidInput: the Python around the fragments is invalid
            print(f"{path}: {error}", file=sys.stderr)
            failed = True
            continue
        except RuntimeError as error:  # black is not installed
            print(error, file=sys.stderr)
            sys.exit(2)

        if args.dry_run:
            print(formatted, end="")
            continue
        if formatted == source:
            continue
        if args.check:
            print(f"would reformat {path}", file=sys.stderr)
            failed = True
            continue
        path.write_text(formatted)
        print(f"reformatted {path}", file=sys.stderr)

    if failed:
        sys.exit(1)


def main():
    args = parse_args()
    assert hasattr(args, "func")
    args.func(args)


if __name__ == "__main__":
    main()
