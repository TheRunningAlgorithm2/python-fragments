from fragments import grammar
from fragments.ast_nodes import ASTFragment, ASTHTMLAttribute, ASTHTMLComment, ASTHTMLElement, ASTHTMLText, ASTInterpolation
from fragments.source import Source


def _transpiled(fragment: ASTFragment) -> ASTFragment:
    """Call transpile so all nodes have transpiled_* fields set for equality comparison."""
    fragment.transpile(0)
    return fragment


def test_comment_standalone():
    source = Source.from_string("<><!-- a note --></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert _transpiled(fragment) == _transpiled(ASTFragment(-1, -1, [
        ASTHTMLComment(-1, -1, " a note ")
    ]))


def test_comment_multiline():
    source = Source.from_string("<><!-- line one\nline two --></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert _transpiled(fragment) == _transpiled(ASTFragment(-1, -1, [
        ASTHTMLComment(-1, -1, " line one\nline two ")
    ]))


def test_comment_inside_element():
    source = Source.from_string("<><div><!-- note --></div></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert _transpiled(fragment) == _transpiled(ASTFragment(-1, -1, [
        ASTHTMLElement(-1, -1, "div", {}, None, None, [
            ASTHTMLComment(-1, -1, " note ")
        ], False)
    ]))


def test_comment_between_elements():
    source = Source.from_string("<><h1>Title</h1><!-- separator --><p>Content</p></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert _transpiled(fragment) == _transpiled(ASTFragment(-1, -1, [
        ASTHTMLElement(-1, -1, "h1", {}, None, None, [ASTHTMLText(-1, -1, "Title")], False),
        ASTHTMLComment(-1, -1, " separator "),
        ASTHTMLElement(-1, -1, "p", {}, None, None, [ASTHTMLText(-1, -1, "Content")], False),
    ]))


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
                    ASTInterpolation(-1, -1, "item in user.items", 1, 1),
                    [
                        ASTHTMLElement(-1, -1, "p", {"style": ASTHTMLAttribute(-1, -1, "style", None, ASTInterpolation(-1, -1, '{"color": "red"}', 1, 1))}, None, None, [ASTInterpolation(-1, -1, "item.name", 1, 1)], False),
                        ASTHTMLElement(-1, -1, "p", {}, ASTInterpolation(-1, -1, "item.description", 1, 1), None, [ASTInterpolation(-1, -1, "item.description", 1, 1)], False),
                        ASTHTMLElement(-1, -1, "p", {}, None, None, [ASTHTMLText(-1, -1, "This is an item")], False),
                        ASTHTMLElement(-1, -1, "input", {}, None, None, [], True),
                    ],
                    False,
                )
            ],
            False,
        )
    ]))
