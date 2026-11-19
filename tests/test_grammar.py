import pytest

from fragments import grammar
from fragments.ast_nodes import (
    ASTChildrenSlot,
    ASTComponent,
    ASTComponentArgument,
    ASTComponentName,
    ASTControlNode,
    ASTCSSText,
    ASTDoctype,
    ASTFragment,
    ASTHTMLAttribute,
    ASTHTMLComment,
    ASTHTMLElement,
    ASTHTMLText,
    ASTInterpolation,
    ASTJSText,
    ASTHTMLChild,
    ASTScript,
    ASTStyle,
    ASTTemplate,
)
from fragments.grammar import ParsingError
from fragments.source import Source
from fragments.transpiled_code_writer import TranspiledCodeWriter


def _transpiled_content(node: ASTHTMLChild | ASTHTMLAttribute | ASTJSText, source_string: str) -> str:
    """Transpile a single node on its own."""
    writer = TranspiledCodeWriter(source_string)
    node.transpile(writer)
    return writer.transpiled_content()


# ---------------------------------------------------------------------------
# Doctype
# ---------------------------------------------------------------------------


def test_doctype_standalone():
    source = Source.from_string("<><!DOCTYPE html></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTDoctype(-1, -1)
    ])


def test_doctype_transpiles_to_literal_string():
    source = Source.from_string("<><!DOCTYPE html></>")
    _, fragment = grammar.expect_fragment(source)
    doctype = fragment.children[0]
    assert isinstance(doctype, ASTDoctype)
    assert _transpiled_content(doctype, source.content) == '"<!DOCTYPE html>"'


def test_doctype_followed_by_element():
    source = Source.from_string("<><!DOCTYPE html><html></html></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTDoctype(-1, -1),
        ASTHTMLElement(-1, -1, "html", {}, [], False),
    ])


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
    assert fragment == ASTFragment(-1, -1, [
        ASTHTMLComment(-1, -1, " a note ")
    ])


def test_comment_multiline():
    source = Source.from_string("<><!-- line one\nline two --></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTHTMLComment(-1, -1, " line one\nline two ")
    ])


def test_comment_multiline_escaped_in_transpile():
    source = Source.from_string("<><!-- line one\nline two --></>")
    _, fragment = grammar.expect_fragment(source)
    comment = fragment.children[0]
    assert isinstance(comment, ASTHTMLComment)
    assert "\\n" in _transpiled_content(comment, source.content)
    assert "\n" not in _transpiled_content(comment, source.content)


def test_comment_inside_element():
    source = Source.from_string("<><div><!-- note --></div></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTHTMLElement(-1, -1, "div", {}, [
            ASTHTMLComment(-1, -1, " note ")
        ], False)
    ])


def test_comment_between_elements():
    source = Source.from_string("<><h1>Title</h1><!-- separator --><p>Content</p></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTHTMLElement(-1, -1, "h1", {}, [ASTHTMLText(-1, -1, "Title")], False),
        ASTHTMLComment(-1, -1, " separator "),
        ASTHTMLElement(-1, -1, "p", {}, [ASTHTMLText(-1, -1, "Content")], False),
    ])


# ---------------------------------------------------------------------------
# HTML element attributes
# ---------------------------------------------------------------------------


def test_html_element_string_attribute():
    source = Source.from_string('<><div class="foo">text</div></>')
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTHTMLElement(-1, -1, "div", {
            "class": ASTHTMLAttribute(-1, -1, "class", '"foo"', None)
        }, [ASTHTMLText(-1, -1, "text")], False)
    ])


def test_html_element_interpolation_attribute():
    source = Source.from_string("<><div class={{ expr }}>text</div></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTHTMLElement(-1, -1, "div", {
            "class": ASTHTMLAttribute(-1, -1, "class", None, ASTInterpolation(-1, -1, -1, "expr"))
        }, [ASTHTMLText(-1, -1, "text")], False)
    ])


def test_html_attribute_multiline_string_literal_escaped_in_transpile():
    source = Source.from_string('<><div class="foo\nbar">text</div></>')
    _, fragment = grammar.expect_fragment(source)
    element = fragment.children[0]
    assert isinstance(element, ASTHTMLElement)
    assert "\\n" in _transpiled_content(element.attributes["class"], source.content)
    assert "\n" not in _transpiled_content(element.attributes["class"], source.content)


def test_html_attribute_tab_escaped_in_transpile():
    source = Source.from_string('<><div class="foo\tbar">text</div></>')
    _, fragment = grammar.expect_fragment(source)
    element = fragment.children[0]
    assert isinstance(element, ASTHTMLElement)
    assert "\\t" in _transpiled_content(element.attributes["class"], source.content)
    assert "\t" not in _transpiled_content(element.attributes["class"], source.content)


def test_html_element_boolean_attribute():
    source = Source.from_string("<><input disabled /></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTHTMLElement(-1, -1, "input", {
            "disabled": ASTHTMLAttribute(-1, -1, "disabled", None, None)
        }, [], True)
    ])


# ---------------------------------------------------------------------------
# if / for control nodes wrapping HTML elements
# ---------------------------------------------------------------------------


def test_html_element_with_if():
    source = Source.from_string("<><div if={{ condition }}>text</div></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTControlNode(-1, -1,
            ASTInterpolation(-1, -1, -1, "condition"),
            None,
            ASTHTMLElement(-1, -1, "div", {}, [ASTHTMLText(-1, -1, "text")], False),
        )
    ])


def test_html_element_self_closing_with_if():
    source = Source.from_string("<><br if={{ condition }} /></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTControlNode(-1, -1,
            ASTInterpolation(-1, -1, -1, "condition"),
            None,
            ASTHTMLElement(-1, -1, "br", {}, [], True),
        )
    ])


def test_html_element_with_for():
    source = Source.from_string("<><li for={{ item in items }}>{{ item }}</li></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTControlNode(-1, -1,
            None,
            ASTInterpolation(-1, -1, -1, "item in items"),
            ASTHTMLElement(-1, -1, "li", {}, [ASTInterpolation(-1, -1, -1, "item")], False),
        )
    ])


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
    assert fragment == ASTFragment(-1, -1, [
        ASTComponent(-1, -1, ASTComponentName(-1, -1, "MyComp"), {}, [], self_closing=True)
    ])


def test_component_with_double_quote_argument():
    source = Source.from_string('<><MyComp name="hello" /></>')
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTComponent(-1, -1, ASTComponentName(-1, -1, "MyComp"), {
            "name": ASTComponentArgument(-1, -1, "name", '"hello"', None)
        }, [], self_closing=True)
    ])


def test_component_with_single_quote_argument():
    source = Source.from_string("<><MyComp name='hello' /></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTComponent(-1, -1, ASTComponentName(-1, -1, "MyComp"), {
            "name": ASTComponentArgument(-1, -1, "name", "'hello'", None)
        }, [], self_closing=True)
    ])


def test_component_with_interpolation_argument():
    source = Source.from_string("<><MyComp value={{ expr }} /></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTComponent(-1, -1, ASTComponentName(-1, -1, "MyComp"), {
            "value": ASTComponentArgument(-1, -1, "value", None, ASTInterpolation(-1, -1, -1, "expr"))
        }, [], self_closing=True)
    ])


def test_component_with_children():
    source = Source.from_string("<><MyComp><p>text</p></MyComp></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTComponent(-1, -1, ASTComponentName(-1, -1, "MyComp"), {}, [
            ASTHTMLElement(-1, -1, "p", {}, [ASTHTMLText(-1, -1, "text")], False)
        ], self_closing=False)
    ])


def test_component_whitespace_stripped_from_children():
    source = Source.from_string("<><MyComp>\n  <p>text</p>\n</MyComp></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTComponent(-1, -1, ASTComponentName(-1, -1, "MyComp"), {}, [
            ASTHTMLElement(-1, -1, "p", {}, [ASTHTMLText(-1, -1, "text")], False)
        ], self_closing=False)
    ])


def test_component_with_if():
    source = Source.from_string("<><MyComp if={{ condition }} /></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTControlNode(-1, -1,
            ASTInterpolation(-1, -1, -1, "condition"),
            None,
            ASTComponent(-1, -1, ASTComponentName(-1, -1, "MyComp"), {}, [], self_closing=True),
        )
    ])


def test_component_with_for():
    source = Source.from_string("<><MyComp for={{ item in items }} /></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTControlNode(-1, -1,
            None,
            ASTInterpolation(-1, -1, -1, "item in items"),
            ASTComponent(-1, -1, ASTComponentName(-1, -1, "MyComp"), {}, [], self_closing=True),
        )
    ])


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
    assert fragment == ASTFragment(-1, -1, [
        ASTChildrenSlot(-1, -1)
    ])


def test_children_slot_transpiles_to_children():
    source = Source.from_string("<><Children... /></>")
    _, fragment = grammar.expect_fragment(source)
    slot = fragment.children[0]
    assert isinstance(slot, ASTChildrenSlot)
    assert _transpiled_content(slot, source.content) == "children"


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
# Template
# ---------------------------------------------------------------------------


def test_template_bare_parses():
    source = Source.from_string("<><Template><p>a</p><p>b</p></Template></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTTemplate(-1, -1, [
            ASTHTMLElement(-1, -1, "p", {}, [ASTHTMLText(-1, -1, "a")], False),
            ASTHTMLElement(-1, -1, "p", {}, [ASTHTMLText(-1, -1, "b")], False),
        ])
    ])


def test_template_empty_parses():
    source = Source.from_string("<><Template></Template></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [ASTTemplate(-1, -1, [])])


def test_template_with_if():
    source = Source.from_string("<><Template if={{ condition }}><p>a</p></Template></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTControlNode(-1, -1,
            ASTInterpolation(-1, -1, -1, "condition"),
            None,
            ASTTemplate(-1, -1, [ASTHTMLElement(-1, -1, "p", {}, [ASTHTMLText(-1, -1, "a")], False)]),
        )
    ])


def test_template_with_for():
    source = Source.from_string("<><Template for={{ item in items }}>{{ item }}</Template></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTControlNode(-1, -1,
            None,
            ASTInterpolation(-1, -1, -1, "item in items"),
            ASTTemplate(-1, -1, [ASTInterpolation(-1, -1, -1, "item")]),
        )
    ])


def test_template_with_if_and_for():
    source = Source.from_string("<><Template if={{ item.visible }} for={{ item in items }}>{{ item }}</Template></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTControlNode(-1, -1,
            ASTInterpolation(-1, -1, -1, "item.visible"),
            ASTInterpolation(-1, -1, -1, "item in items"),
            ASTTemplate(-1, -1, [ASTInterpolation(-1, -1, -1, "item")]),
        )
    ])


def test_template_whitespace_in_closing_tag():
    source = Source.from_string("<><Template></ Template ></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [ASTTemplate(-1, -1, [])])


def test_template_nested():
    source = Source.from_string("<><Template if={{ a }}><Template for={{ x in xs }}>{{ x }}</Template></Template></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    outer = fragment.children[0]
    assert isinstance(outer, ASTControlNode)
    assert isinstance(outer.child, ASTTemplate)
    inner = outer.child.children[0]
    assert isinstance(inner, ASTControlNode)
    assert isinstance(inner.child, ASTTemplate)


def test_template_inside_element():
    source = Source.from_string("<><ul><Template for={{ x in xs }}><li>{{ x }}</li></Template></ul></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    element = fragment.children[0]
    assert isinstance(element, ASTHTMLElement)
    assert isinstance(element.children[0], ASTControlNode)


def test_template_prefixed_component_name_is_component():
    source = Source.from_string("<><TemplateCard /></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert isinstance(fragment.children[0], ASTComponent)


def test_template_rejects_other_attributes():
    with pytest.raises(ParsingError, match="only accepts if and for"):
        grammar.expect_fragment(Source.from_string('<><Template class="x"></Template></>'))


def test_template_rejects_string_literal_control_attribute():
    with pytest.raises(ParsingError, match="must be an interpolation"):
        grammar.expect_fragment(Source.from_string('<><Template if="condition"></Template></>'))


def test_template_rejects_self_closing():
    with pytest.raises(ParsingError, match="cannot be self-closing"):
        grammar.expect_fragment(Source.from_string("<><Template if={{ condition }} /></>"))


def test_template_mismatched_closing_tag():
    with pytest.raises(ParsingError):
        grammar.expect_fragment(Source.from_string("<><Template></div></>"))


# ---------------------------------------------------------------------------
# Scripts and styles
# ---------------------------------------------------------------------------


def test_script_body_is_raw_text():
    source = Source.from_string("<><script>if (a < b) { f('{{ x }}', '</>', '<!--'); }</script></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTScript(-1, -1, {}, ASTJSText(-1, -1, "if (a < b) { f('{{ x }}', '</>', '<!--'); }"))
    ])


def test_style_body_is_raw_text():
    source = Source.from_string("<><style>.card > h2 { margin: 0; }</style></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTStyle(-1, -1, {}, ASTCSSText(-1, -1, ".card > h2 { margin: 0; }"))
    ])


def test_script_body_whitespace_is_preserved():
    source = Source.from_string("<><script>\n    run();\n  </script></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTScript(-1, -1, {}, ASTJSText(-1, -1, "\n    run();\n  "))
    ])


def test_script_empty_body():
    source = Source.from_string("<><script></script></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTScript(-1, -1, {}, ASTJSText(-1, -1, ""))
    ])


def test_script_body_source_offsets():
    source = Source.from_string("<><script>run()</script></>")
    _, fragment = grammar.expect_fragment(source)
    script = fragment.children[0]
    assert isinstance(script, ASTScript)
    assert script.body is not None
    assert (script.body.source_start, script.body.source_end) == (10, 15)


def test_script_closing_tag_allows_whitespace():
    source = Source.from_string("<><script>run()</script \n></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTScript(-1, -1, {}, ASTJSText(-1, -1, "run()"))
    ])


def test_script_body_ends_at_first_closing_tag():
    source = Source.from_string("<><script>a</script><p>b</p></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTScript(-1, -1, {}, ASTJSText(-1, -1, "a")),
        ASTHTMLElement(-1, -1, "p", {}, [ASTHTMLText(-1, -1, "b")], False),
    ])


def test_script_closing_tag_is_case_sensitive():
    with pytest.raises(ParsingError):
        grammar.expect_fragment(Source.from_string("<><script>run()</SCRIPT></>"))


def test_script_closing_tag_rejects_slash():
    with pytest.raises(ParsingError):
        grammar.expect_fragment(Source.from_string("<><script>run()</script/></>"))


def test_style_body_not_ended_by_script_closing_tag():
    source = Source.from_string("<><style>a</script>b</style></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTStyle(-1, -1, {}, ASTCSSText(-1, -1, "a</script>b"))
    ])


def test_script_unclosed_points_at_opening_tag():
    with pytest.raises(ParsingError) as error:
        grammar.expect_fragment(Source.from_string("<><script>run()</>"))
    assert str(error.value) == "Unclosed <script> element"
    assert error.value.source_start == 2


def test_style_unclosed_points_at_opening_tag():
    with pytest.raises(ParsingError) as error:
        grammar.expect_fragment(Source.from_string("<><style>body {}</>"))
    assert str(error.value) == "Unclosed <style> element"
    assert error.value.source_start == 2


def test_script_attributes():
    source = Source.from_string('<><script src="app.js" nonce={{ nonce }} defer></script></>')
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTScript(-1, -1, {
            "src": ASTHTMLAttribute(-1, -1, "src", '"app.js"', None),
            "nonce": ASTHTMLAttribute(-1, -1, "nonce", None, ASTInterpolation(-1, -1, -1, "nonce")),
            "defer": ASTHTMLAttribute(-1, -1, "defer", None, None),
        }, ASTJSText(-1, -1, ""))
    ])


def test_style_with_if():
    source = Source.from_string("<><style if={{ dark }}>body {}</style></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTControlNode(-1, -1, ASTInterpolation(-1, -1, -1, "dark"), None,
            ASTStyle(-1, -1, {}, ASTCSSText(-1, -1, "body {}"))
        )
    ])


def test_script_self_closing_is_kept():
    source = Source.from_string('<><script src="app.js" /></>')
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTScript(-1, -1, {
            "src": ASTHTMLAttribute(-1, -1, "src", '"app.js"', None),
        }, None)
    ])


def test_element_prefixed_with_script_is_normal_element():
    source = Source.from_string("<><scripts><b>x</b></scripts></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTHTMLElement(-1, -1, "scripts", {}, [
            ASTHTMLElement(-1, -1, "b", {}, [ASTHTMLText(-1, -1, "x")], False)
        ], False)
    ])


def test_script_body_transpiles_to_python_literal():
    source = Source.from_string("<><script>f(\"a\\n\", 'b')</script></>")
    _, fragment = grammar.expect_fragment(source)
    script = fragment.children[0]
    assert isinstance(script, ASTScript)
    assert script.body is not None
    assert _transpiled_content(script.body, source.content) == repr("f(\"a\\n\", 'b')")


# ---------------------------------------------------------------------------
# HTML text
# ---------------------------------------------------------------------------


def test_html_text_single_line():
    source = Source.from_string("<><p>hello world</p></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTHTMLElement(-1, -1, "p", {}, [ASTHTMLText(-1, -1, "hello world")], False)
    ])


def test_html_text_multiline():
    source = Source.from_string("<><p>hello\nworld</p></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTHTMLElement(-1, -1, "p", {}, [ASTHTMLText(-1, -1, "hello\nworld")], False)
    ])


def test_html_text_multiline_before_interpolation():
    source = Source.from_string("<><p>hello\n{{ name }}</p></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTHTMLElement(-1, -1, "p", {}, [
            ASTHTMLText(-1, -1, "hello\n"),
            ASTInterpolation(-1, -1, -1, "name"),
        ], False)
    ])


def test_html_text_multiline_before_child_element():
    source = Source.from_string("<><p>hello\n<span>world</span></p></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTHTMLElement(-1, -1, "p", {}, [
            ASTHTMLText(-1, -1, "hello\n"),
            ASTHTMLElement(-1, -1, "span", {}, [ASTHTMLText(-1, -1, "world")], False),
        ], False)
    ])


def test_whitespace_between_adjacent_interpolations_is_preserved():
    source = Source.from_string("<><p>{{ a }} {{ b }}</p></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTHTMLElement(-1, -1, "p", {}, [
            ASTInterpolation(-1, -1, -1, "a"),
            ASTHTMLText(-1, -1, " "),
            ASTInterpolation(-1, -1, -1, "b"),
        ], False)
    ])


def test_interpolation_no_trailing_whitespace():
    source = Source.from_string("<><NotificationBar user={{ user}} /></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTComponent(-1, -1, ASTComponentName(-1, -1, "NotificationBar"), {
            "user": ASTComponentArgument(-1, -1, "user", None, ASTInterpolation(-1, -1, -1, "user"))
        }, [], self_closing=True)
    ])


def test_interpolation_no_leading_whitespace():
    source = Source.from_string("<><NotificationBar user={{user }} /></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTComponent(-1, -1, ASTComponentName(-1, -1, "NotificationBar"), {
            "user": ASTComponentArgument(-1, -1, "user", None, ASTInterpolation(-1, -1, -1, "user"))
        }, [], self_closing=True)
    ])


def test_interpolation_no_whitespace():
    source = Source.from_string("<><NotificationBar user={{user}} /></>")
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()
    assert fragment == ASTFragment(-1, -1, [
        ASTComponent(-1, -1, ASTComponentName(-1, -1, "NotificationBar"), {
            "user": ASTComponentArgument(-1, -1, "user", None, ASTInterpolation(-1, -1, -1, "user"))
        }, [], self_closing=True)
    ])


# ---------------------------------------------------------------------------
# Full integration (updated for new AST structure)
# ---------------------------------------------------------------------------


def test_full():
    with open("tests/data/full.py", "r") as f:
        source = Source.from_string(f.read())
    source, fragment = grammar.expect_fragment(source)
    assert source.at_end()

    assert fragment == ASTFragment(-1, -1, [
        ASTHTMLElement(-1, -1, "div", {
            "classes": ASTHTMLAttribute(-1, -1, "classes", '"flex flex-col gap-3"', None)
        }, [
            ASTControlNode(-1, -1,
                None,
                ASTInterpolation(-1, -1, -1, "item in user.items"),
                ASTHTMLElement(-1, -1, "div", {
                    "classes": ASTHTMLAttribute(-1, -1, "classes", '"p-3 rounded-lg bg-gray-800"', None)
                }, [
                    ASTHTMLElement(-1, -1, "p", {
                        "style": ASTHTMLAttribute(-1, -1, "style", None, ASTInterpolation(-1, -1, -1, '{"color": "red"}'))
                    }, [ASTInterpolation(-1, -1, -1, "item.name")], False),
                    ASTControlNode(-1, -1,
                        ASTInterpolation(-1, -1, -1, "item.description"),
                        None,
                        ASTHTMLElement(-1, -1, "p", {}, [
                            ASTInterpolation(-1, -1, -1, "item.description")
                        ], False),
                    ),
                    ASTHTMLElement(-1, -1, "p", {}, [ASTHTMLText(-1, -1, "This is an item")], False),
                    ASTHTMLElement(-1, -1, "input", {}, [], True),
                ], False),
            )
        ], False)
    ])
