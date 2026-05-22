import argparse

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


def main():
    args = parse_args()
    assert hasattr(args, "func")
    args.func(args)


if __name__ == "__main__":
    main()
