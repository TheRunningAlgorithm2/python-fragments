import pytest

from fragments import grammar
from fragments.ast_nodes import (
    ASTChildrenSlot,
    ASTComponent,
    ASTComponentArgument,
    ASTComponentName,
    ASTControlNode,
    ASTDoctype,
    ASTFragment,
    ASTHTMLAttribute,
    ASTHTMLComment,
    ASTHTMLElement,
    ASTHTMLText,
    ASTInterpolation,
)
from fragments.grammar import ParsingError
from fragments.source import Source


def _transpiled(fragment: ASTFragment) -> ASTFragment:
    """Call transpile so all nodes have transpiled_* fields set for equality comparison."""
    fragment.transpile(0)
    return fragment


# ---------------------------------------------------------------------------
# Doctype
# ---------------------------------------------------------------------------


def test_doctype_standalone():
    source = Source.from_string("<><!DOCTYPE html></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert _transpiled(fragment) == _transpiled(ASTFragment(-1, -1, [
        ASTDoctype(-1, -1)
    ]))


def test_doctype_transpiles_to_literal_string():
    source = Source.from_string("<><!DOCTYPE html></>")
    _, fragment = grammar.expect_fragment(source)
    fragment.transpile(0)
    doctype = fragment.children[0]
    assert isinstance(doctype, ASTDoctype)
    assert doctype.transpiled_content == '"<!DOCTYPE html>"'


def test_doctype_followed_by_element():
    source = Source.from_string("<><!DOCTYPE html><html></html></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert _transpiled(fragment) == _transpiled(ASTFragment(-1, -1, [
        ASTDoctype(-1, -1),
        ASTHTMLElement(-1, -1, "html", {}, [], False),
    ]))


def test_doctype_not_confused_with_comment():
    source = Source.from_string("<><!DOCTYPE html><!-- a note --></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert isinstance(fragment.children[0], ASTDoctype)
    assert isinstance(fragment.children[1], ASTHTMLComment)


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------


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


def test_comment_multiline_escaped_in_transpile():
    source = Source.from_string("<><!-- line one\nline two --></>")
    _, fragment = grammar.expect_fragment(source)
    fragment.transpile(0)
    comment = fragment.children[0]
    assert isinstance(comment, ASTHTMLComment)
    assert "\\n" in comment.transpiled_content
    assert "\n" not in comment.transpiled_content


def test_comment_inside_element():
    source = Source.from_string("<><div><!-- note --></div></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert _transpiled(fragment) == _transpiled(ASTFragment(-1, -1, [
        ASTHTMLElement(-1, -1, "div", {}, [
            ASTHTMLComment(-1, -1, " note ")
        ], False)
    ]))


def test_comment_between_elements():
    source = Source.from_string("<><h1>Title</h1><!-- separator --><p>Content</p></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert _transpiled(fragment) == _transpiled(ASTFragment(-1, -1, [
        ASTHTMLElement(-1, -1, "h1", {}, [ASTHTMLText(-1, -1, "Title")], False),
        ASTHTMLComment(-1, -1, " separator "),
        ASTHTMLElement(-1, -1, "p", {}, [ASTHTMLText(-1, -1, "Content")], False),
    ]))


# ---------------------------------------------------------------------------
# HTML element attributes
# ---------------------------------------------------------------------------


def test_html_element_string_attribute():
    source = Source.from_string('<><div class="foo">text</div></>')
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert _transpiled(fragment) == _transpiled(ASTFragment(-1, -1, [
        ASTHTMLElement(-1, -1, "div", {
            "class": ASTHTMLAttribute(-1, -1, "class", '"foo"', None)
        }, [ASTHTMLText(-1, -1, "text")], False)
    ]))


def test_html_element_interpolation_attribute():
    source = Source.from_string("<><div class={{ expr }}>text</div></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert _transpiled(fragment) == _transpiled(ASTFragment(-1, -1, [
        ASTHTMLElement(-1, -1, "div", {
            "class": ASTHTMLAttribute(-1, -1, "class", None, ASTInterpolation(-1, -1, "expr", 1, 1))
        }, [ASTHTMLText(-1, -1, "text")], False)
    ]))


def test_html_attribute_multiline_string_literal_escaped_in_transpile():
    source = Source.from_string('<><div class="foo\nbar">text</div></>')
    _, fragment = grammar.expect_fragment(source)
    fragment.transpile(0)
    element = fragment.children[0]
    assert isinstance(element, ASTHTMLElement)
    assert "\\n" in element.attributes["class"].transpiled_content
    assert "\n" not in element.attributes["class"].transpiled_content


def test_html_attribute_tab_escaped_in_transpile():
    source = Source.from_string('<><div class="foo\tbar">text</div></>')
    _, fragment = grammar.expect_fragment(source)
    fragment.transpile(0)
    element = fragment.children[0]
    assert isinstance(element, ASTHTMLElement)
    assert "\\t" in element.attributes["class"].transpiled_content
    assert "\t" not in element.attributes["class"].transpiled_content


def test_html_element_boolean_attribute():
    source = Source.from_string("<><input disabled /></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert _transpiled(fragment) == _transpiled(ASTFragment(-1, -1, [
        ASTHTMLElement(-1, -1, "input", {
            "disabled": ASTHTMLAttribute(-1, -1, "disabled", None, None)
        }, [], True)
    ]))


# ---------------------------------------------------------------------------
# if / for control nodes wrapping HTML elements
# ---------------------------------------------------------------------------


def test_html_element_with_if():
    source = Source.from_string("<><div if={{ condition }}>text</div></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert _transpiled(fragment) == _transpiled(ASTFragment(-1, -1, [
        ASTControlNode(-1, -1,
            ASTInterpolation(-1, -1, "condition", 1, 1),
            None,
            ASTHTMLElement(-1, -1, "div", {}, [ASTHTMLText(-1, -1, "text")], False),
        )
    ]))


def test_html_element_self_closing_with_if():
    source = Source.from_string("<><br if={{ condition }} /></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert _transpiled(fragment) == _transpiled(ASTFragment(-1, -1, [
        ASTControlNode(-1, -1,
            ASTInterpolation(-1, -1, "condition", 1, 1),
            None,
            ASTHTMLElement(-1, -1, "br", {}, [], True),
        )
    ]))


def test_html_element_with_for():
    source = Source.from_string("<><li for={{ item in items }}>{{ item }}</li></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert _transpiled(fragment) == _transpiled(ASTFragment(-1, -1, [
        ASTControlNode(-1, -1,
            None,
            ASTInterpolation(-1, -1, "item in items", 1, 1),
            ASTHTMLElement(-1, -1, "li", {}, [ASTInterpolation(-1, -1, "item", 1, 1)], False),
        )
    ]))


def test_html_element_with_if_and_for():
    """Both if and for attributes should be extracted into the control node."""
    source = Source.from_string("<><li if={{ cond }} for={{ item in items }}>{{ item }}</li></>")
    _, fragment = grammar.expect_fragment(source)
    control_node = fragment.children[0]
    assert isinstance(control_node, ASTControlNode)
    assert control_node.if_interpolation is not None
    assert control_node.for_interpolation is not None
    assert control_node.if_interpolation.expression == "cond"
    assert control_node.for_interpolation.expression == "item in items"


def test_html_element_if_not_in_attributes():
    """The if attribute must be extracted from element.attributes into the control node."""
    source = Source.from_string("<><div if={{ cond }}>text</div></>")
    _, fragment = grammar.expect_fragment(source)
    control_node = fragment.children[0]
    assert isinstance(control_node, ASTControlNode)
    assert "if" not in control_node.child.attributes


def test_html_element_for_not_in_attributes():
    """The for attribute must be extracted from element.attributes into the control node."""
    source = Source.from_string("<><div for={{ item in items }}>text</div></>")
    _, fragment = grammar.expect_fragment(source)
    control_node = fragment.children[0]
    assert isinstance(control_node, ASTControlNode)
    assert "for" not in control_node.child.attributes


# ---------------------------------------------------------------------------
# Components
# ---------------------------------------------------------------------------


def test_component_self_closing():
    source = Source.from_string("<><MyComp /></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert _transpiled(fragment) == _transpiled(ASTFragment(-1, -1, [
        ASTComponent(-1, -1, ASTComponentName(-1, -1, "MyComp"), {}, [])
    ]))


def test_component_with_double_quote_argument():
    source = Source.from_string('<><MyComp name="hello" /></>')
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert _transpiled(fragment) == _transpiled(ASTFragment(-1, -1, [
        ASTComponent(-1, -1, ASTComponentName(-1, -1, "MyComp"), {
            "name": ASTComponentArgument(-1, -1, "name", '"hello"', None)
        }, [])
    ]))


def test_component_with_single_quote_argument():
    source = Source.from_string("<><MyComp name='hello' /></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert _transpiled(fragment) == _transpiled(ASTFragment(-1, -1, [
        ASTComponent(-1, -1, ASTComponentName(-1, -1, "MyComp"), {
            "name": ASTComponentArgument(-1, -1, "name", "'hello'", None)
        }, [])
    ]))


def test_component_with_interpolation_argument():
    source = Source.from_string("<><MyComp value={{ expr }} /></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert _transpiled(fragment) == _transpiled(ASTFragment(-1, -1, [
        ASTComponent(-1, -1, ASTComponentName(-1, -1, "MyComp"), {
            "value": ASTComponentArgument(-1, -1, "value", None, ASTInterpolation(-1, -1, "expr", 1, 1))
        }, [])
    ]))


def test_component_with_children():
    source = Source.from_string("<><MyComp><p>text</p></MyComp></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert _transpiled(fragment) == _transpiled(ASTFragment(-1, -1, [
        ASTComponent(-1, -1, ASTComponentName(-1, -1, "MyComp"), {}, [
            ASTHTMLElement(-1, -1, "p", {}, [ASTHTMLText(-1, -1, "text")], False)
        ])
    ]))


def test_component_whitespace_stripped_from_children():
    source = Source.from_string("<><MyComp>\n  <p>text</p>\n</MyComp></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert _transpiled(fragment) == _transpiled(ASTFragment(-1, -1, [
        ASTComponent(-1, -1, ASTComponentName(-1, -1, "MyComp"), {}, [
            ASTHTMLElement(-1, -1, "p", {}, [ASTHTMLText(-1, -1, "text")], False)
        ])
    ]))


def test_component_with_if():
    source = Source.from_string("<><MyComp if={{ condition }} /></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert _transpiled(fragment) == _transpiled(ASTFragment(-1, -1, [
        ASTControlNode(-1, -1,
            ASTInterpolation(-1, -1, "condition", 1, 1),
            None,
            ASTComponent(-1, -1, ASTComponentName(-1, -1, "MyComp"), {}, []),
        )
    ]))


def test_component_with_for():
    source = Source.from_string("<><MyComp for={{ item in items }} /></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert _transpiled(fragment) == _transpiled(ASTFragment(-1, -1, [
        ASTControlNode(-1, -1,
            None,
            ASTInterpolation(-1, -1, "item in items", 1, 1),
            ASTComponent(-1, -1, ASTComponentName(-1, -1, "MyComp"), {}, []),
        )
    ]))


def test_component_if_not_in_arguments():
    """if must be extracted from component arguments into the control node."""
    source = Source.from_string("<><MyComp if={{ cond }} value={{ val }} /></>")
    _, fragment = grammar.expect_fragment(source)
    control_node = fragment.children[0]
    assert isinstance(control_node, ASTControlNode)
    assert "if" not in control_node.child.arguments


def test_component_mismatched_closing_tag():
    with pytest.raises(ParsingError):
        grammar.expect_fragment(Source.from_string("<><MyComp></Other></>"))


def test_lowercase_not_parsed_as_component():
    source = Source.from_string("<><div>text</div></>")
    _, fragment = grammar.expect_fragment(source)
    assert isinstance(fragment.children[0], ASTHTMLElement)


# ---------------------------------------------------------------------------
# Children slot
# ---------------------------------------------------------------------------


def test_children_slot_parses():
    source = Source.from_string("<><Children... /></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert _transpiled(fragment) == _transpiled(ASTFragment(-1, -1, [
        ASTChildrenSlot(-1, -1)
    ]))


def test_children_slot_transpiles_to_children():
    source = Source.from_string("<><Children... /></>")
    _, fragment = grammar.expect_fragment(source)
    fragment.transpile(0)
    slot = fragment.children[0]
    assert isinstance(slot, ASTChildrenSlot)
    assert slot.transpiled_content == "children"


def test_children_slot_multiple_in_one_fragment():
    source = Source.from_string("<><Children... /><Children... /></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert len(fragment.children) == 2
    assert all(isinstance(child, ASTChildrenSlot) for child in fragment.children)


def test_children_slot_not_confused_with_component():
    source = Source.from_string("<><Children /></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert isinstance(fragment.children[0], ASTComponent)


def test_children_slot_inside_element():
    source = Source.from_string("<><div><Children... /></div></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    element = fragment.children[0]
    assert isinstance(element, ASTHTMLElement)
    assert isinstance(element.children[0], ASTChildrenSlot)


# ---------------------------------------------------------------------------
# HTML text
# ---------------------------------------------------------------------------


def test_html_text_single_line():
    source = Source.from_string("<><p>hello world</p></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert _transpiled(fragment) == _transpiled(ASTFragment(-1, -1, [
        ASTHTMLElement(-1, -1, "p", {}, [ASTHTMLText(-1, -1, "hello world")], False)
    ]))


def test_html_text_multiline():
    source = Source.from_string("<><p>hello\nworld</p></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert _transpiled(fragment) == _transpiled(ASTFragment(-1, -1, [
        ASTHTMLElement(-1, -1, "p", {}, [ASTHTMLText(-1, -1, "hello\nworld")], False)
    ]))


def test_html_text_multiline_before_interpolation():
    source = Source.from_string("<><p>hello\n{{ name }}</p></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert _transpiled(fragment) == _transpiled(ASTFragment(-1, -1, [
        ASTHTMLElement(-1, -1, "p", {}, [
            ASTHTMLText(-1, -1, "hello\n"),
            ASTInterpolation(-1, -1, "name", 1, 1),
        ], False)
    ]))


def test_html_text_multiline_before_child_element():
    source = Source.from_string("<><p>hello\n<span>world</span></p></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert _transpiled(fragment) == _transpiled(ASTFragment(-1, -1, [
        ASTHTMLElement(-1, -1, "p", {}, [
            ASTHTMLText(-1, -1, "hello\n"),
            ASTHTMLElement(-1, -1, "span", {}, [ASTHTMLText(-1, -1, "world")], False),
        ], False)
    ]))


def test_whitespace_between_adjacent_interpolations_is_preserved():
    source = Source.from_string("<><p>{{ a }} {{ b }}</p></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert _transpiled(fragment) == _transpiled(ASTFragment(-1, -1, [
        ASTHTMLElement(-1, -1, "p", {}, [
            ASTInterpolation(-1, -1, "a", 1, 1),
            ASTHTMLText(-1, -1, " "),
            ASTInterpolation(-1, -1, "b", 1, 1),
        ], False)
    ]))


def test_interpolation_no_trailing_whitespace():
    source = Source.from_string("<><NotificationBar user={{ user}} /></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert _transpiled(fragment) == _transpiled(ASTFragment(-1, -1, [
        ASTComponent(-1, -1, ASTComponentName(-1, -1, "NotificationBar"), {
            "user": ASTComponentArgument(-1, -1, "user", None, ASTInterpolation(-1, -1, "user", 1, 0))
        }, [])
    ]))


def test_interpolation_no_leading_whitespace():
    source = Source.from_string("<><NotificationBar user={{user }} /></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert _transpiled(fragment) == _transpiled(ASTFragment(-1, -1, [
        ASTComponent(-1, -1, ASTComponentName(-1, -1, "NotificationBar"), {
            "user": ASTComponentArgument(-1, -1, "user", None, ASTInterpolation(-1, -1, "user", 0, 1))
        }, [])
    ]))


def test_interpolation_no_whitespace():
    source = Source.from_string("<><NotificationBar user={{user}} /></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert _transpiled(fragment) == _transpiled(ASTFragment(-1, -1, [
        ASTComponent(-1, -1, ASTComponentName(-1, -1, "NotificationBar"), {
            "user": ASTComponentArgument(-1, -1, "user", None, ASTInterpolation(-1, -1, "user", 0, 0))
        }, [])
    ]))


# ---------------------------------------------------------------------------
# Full integration (updated for new AST structure)
# ---------------------------------------------------------------------------


def test_full():
    with open("tests/data/full.py", "r") as f:
        source = Source.from_string(f.read())
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()

    assert _transpiled(fragment) == _transpiled(ASTFragment(-1, -1, [
        ASTHTMLElement(-1, -1, "div", {
            "classes": ASTHTMLAttribute(-1, -1, "classes", '"flex flex-col gap-3"', None)
        }, [
            ASTControlNode(-1, -1,
                None,
                ASTInterpolation(-1, -1, "item in user.items", 1, 1),
                ASTHTMLElement(-1, -1, "div", {
                    "classes": ASTHTMLAttribute(-1, -1, "classes", '"p-3 rounded-lg bg-gray-800"', None)
                }, [
                    ASTHTMLElement(-1, -1, "p", {
                        "style": ASTHTMLAttribute(-1, -1, "style", None, ASTInterpolation(-1, -1, '{"color": "red"}', 1, 1))
                    }, [ASTInterpolation(-1, -1, "item.name", 1, 1)], False),
                    ASTControlNode(-1, -1,
                        ASTInterpolation(-1, -1, "item.description", 1, 1),
                        None,
                        ASTHTMLElement(-1, -1, "p", {}, [
                            ASTInterpolation(-1, -1, "item.description", 1, 1)
                        ], False),
                    ),
                    ASTHTMLElement(-1, -1, "p", {}, [ASTHTMLText(-1, -1, "This is an item")], False),
                    ASTHTMLElement(-1, -1, "input", {}, [], True),
                ], False),
            )
        ], False)
    ]))
