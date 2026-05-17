from fragments import grammar
from fragments.ast_nodes import ASTFragment, ASTHTMLAttribute, ASTHTMLElement, ASTHTMLText, ASTInterpolation
from fragments.source import Source


def _transpiled(fragment: ASTFragment) -> ASTFragment:
    """Call transpile so all nodes have transpiled_* fields set for equality comparison."""
    fragment.transpile(0)
    return fragment


def test_full():
    """A fragment that has only one child which is a single HTML Element."""
    with open("tests/data/full.py", "r") as f:
        source = Source.from_string(f.read())
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()

    assert _transpiled(fragment) == _transpiled(ASTFragment(-1, -1, [
        ASTHTMLElement(
            -1,
            -1,
            "div",
            {"classes": ASTHTMLAttribute(-1, -1, "classes", "flex flex-col gap-3", None)},
            None,
            None,
            [
                ASTHTMLElement(
                    -1,
                    -1,
                    "div",
                    {"classes": ASTHTMLAttribute(-1, -1, "classes", "p-3 rounded-lg bg-gray-800", None)},
                    None,
                    ASTInterpolation(-1, -1, "item in user.items"),
                    [
                        ASTHTMLElement(-1, -1, "p", {"style": ASTHTMLAttribute(-1, -1, "style", None, ASTInterpolation(-1, -1, '{"color": "red"}'))}, None, None, [ASTInterpolation(-1, -1, "item.name")], False),
                        ASTHTMLElement(-1, -1, "p", {}, ASTInterpolation(-1, -1, "item.description"), None, [ASTInterpolation(-1, -1, "item.description")], False),
                        ASTHTMLElement(-1, -1, "p", {}, None, None, [ASTHTMLText(-1, -1, "This is an item")], False),
                        ASTHTMLElement(-1, -1, "input", {}, None, None, [], True),
                    ],
                    False,
                )
            ],
            False,
        )
    ]))
