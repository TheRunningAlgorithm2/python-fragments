import argparse

from fragments import grammar


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser("fragments", description="Fragments transpilation CLI tool")
    parser.add_argument("--input", type=str, required=True)
    return parser.parse_args()


def main():
    args = parse_args()
    with open(args.input, "r") as f:
        source = f.read()
    source, fragment = grammar.expect_fragment(source)
    print(fragment.template(0))


if __name__ == "__main__":
    main()
