from fragments import grammar
from fragments.nodes import ASTHTMLAttribute, ASTHTMLElement, ASTHTMLText, ASTInterpolation


def test_full():
    """A fragment that has only one child which is a single HTML Element."""
    with open("tests/data/full.py", "r") as f:
        source = f.read()
    source, fragment = grammar.expect_fragment(source)
    assert source == ""
    assert fragment.children == [
        ASTHTMLElement(
            "div",
            {"classes": ASTHTMLAttribute("classes", "flex flex-col gap-3", None)},
            [
                ASTHTMLElement(
                    "div",
                    {"for": ASTHTMLAttribute("for", None, ASTInterpolation("item in user.items")), "classes": ASTHTMLAttribute("classes", "p-3 rounded-lg bg-gray-800", None)},
                    [
                        ASTHTMLElement("p", {"style": ASTHTMLAttribute("style", None, ASTInterpolation('{"color": "red"}'))}, [ASTInterpolation("item.name")], False),
                        ASTHTMLElement("p", {"if": ASTHTMLAttribute("if", None, ASTInterpolation("item.description"))}, [ASTInterpolation("item.description")], False),
                        ASTHTMLElement("p", {}, [ASTHTMLText("This is an item")], False),
                        ASTHTMLElement("input", {}, [], True),
                    ],
                    False,
                )
            ],
            False,
        )
    ]
