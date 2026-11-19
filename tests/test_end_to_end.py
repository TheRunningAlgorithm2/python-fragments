from fragments.transpiler import transpile


def render(source_str: str, **variables: object) -> str:
    """Transpile a fragment source string, execute it, and return the result."""
    namespace: dict[str, object] = dict(variables)
    exec(transpile(f"result = {source_str.strip()}"), namespace)
    return str(namespace["result"])


# ---------------------------------------------------------------------------
# Basic elements
# ---------------------------------------------------------------------------


def test_single_element():
    assert render("<><h1>Hello</h1></>") == "<h1>Hello</h1>"


def test_multiple_siblings():
    assert render("<><h1>Title</h1><p>Body</p></>") == "<h1>Title</h1><p>Body</p>"


def test_nested_elements():
    assert render("<><div><p>text</p></div></>") == "<div><p>text</p></div>"


def test_self_closing_element():
    assert render("<><br /></>") == "<br />"


def test_empty_fragment():
    assert render("<></>") == ""


# ---------------------------------------------------------------------------
# Interpolation
# ---------------------------------------------------------------------------


def test_interpolation():
    assert render("<><p>{{ name }}</p></>", name="World") == "<p>World</p>"


def test_multiple_interpolations():
    assert render("<><p>{{ a }} and {{ b }}</p></>", a="foo", b="bar") == "<p>foo and bar</p>"


def test_text_space_before_element():
    assert render("<>Icon: <i></i></>") == "Icon: <i></i>"


def test_text_space_after_element():
    assert render("<><i></i> text</>") == "<i></i> text"


def test_text_space_around_element():
    assert render("<>before <i>em</i> after</>") == "before <i>em</i> after"


# ---------------------------------------------------------------------------
# Control flow — if
# ---------------------------------------------------------------------------


def test_if_true():
    assert render("<><p if={{ cond }}>yes</p></>", cond=True) == "<p>yes</p>"


def test_if_false():
    assert render("<><p if={{ cond }}>yes</p></>", cond=False) == ""


def test_if_true_with_sibling():
    result = render("<><p if={{ cond }}>yes</p><p>always</p></>", cond=True)
    assert result == "<p>yes</p><p>always</p>"


def test_if_false_with_sibling():
    result = render("<><p if={{ cond }}>yes</p><p>always</p></>", cond=False)
    assert result == "<p>always</p>"


def test_if_true_with_preceding_sibling():
    result = render("<><p>always</p><p if={{ cond }}>maybe</p></>", cond=True)
    assert result == "<p>always</p><p>maybe</p>"


def test_if_false_with_preceding_sibling():
    result = render("<><p>always</p><p if={{ cond }}>maybe</p></>", cond=False)
    assert result == "<p>always</p>"


def test_if_between_siblings():
    result = render("<><p>before</p><p if={{ cond }}>maybe</p><p>after</p></>", cond=True)
    assert result == "<p>before</p><p>maybe</p><p>after</p>"

    result = render("<><p>before</p><p if={{ cond }}>maybe</p><p>after</p></>", cond=False)
    assert result == "<p>before</p><p>after</p>"


# ---------------------------------------------------------------------------
# Control flow — for
# ---------------------------------------------------------------------------


def test_for_loop():
    result = render("<><li for={{ item in items }}>{{ item }}</li></>", items=["a", "b", "c"])
    assert result == "<li>a</li><li>b</li><li>c</li>"


def test_for_loop_with_sibling():
    result = render("<><h1>List</h1><li for={{ item in items }}>{{ item }}</li></>", items=["x", "y"])
    assert result == "<h1>List</h1><li>x</li><li>y</li>"


def test_for_loop_empty():
    assert render("<><li for={{ item in items }}>{{ item }}</li></>", items=[]) == ""


# ---------------------------------------------------------------------------
# Control flow: for with if
# ---------------------------------------------------------------------------


def test_for_with_if_filters_each_item():
    result = render("<><li for={{ number in numbers }} if={{ number % 2 == 0 }}>{{ number }}</li></>", numbers=[1, 2, 3, 4])
    assert result == "<li>2</li><li>4</li>"


def test_for_with_if_attribute_order_does_not_matter():
    result = render("<><li if={{ number % 2 == 0 }} for={{ number in numbers }}>{{ number }}</li></>", numbers=[1, 2, 3, 4])
    assert result == "<li>2</li><li>4</li>"


def test_for_with_if_on_component():
    def Item(value: int) -> str:
        return f"<b>{value}</b>"

    result = render("<><Item for={{ number in numbers }} if={{ number > 1 }} value={{ number }} /></>", numbers=[1, 2, 3], Item=Item)
    assert result == "<b>2</b><b>3</b>"


def test_if_with_nested_ternary_condition():
    result = render("<><p if={{ first if use_first else second }}>yes</p></>", use_first=False, first=True, second=False)
    assert result == ""


def test_for_with_if_nested_ternary_condition():
    result = render("<><li for={{ number in numbers }} if={{ number if use_number else 0 }}>{{ number }}</li></>", numbers=[0, 1, 2], use_number=True)
    assert result == "<li>1</li><li>2</li>"


# ---------------------------------------------------------------------------
# Template
# ---------------------------------------------------------------------------


def test_template_bare_renders_children():
    assert render("<><Template><p>a</p><p>b</p></Template></>") == "<p>a</p><p>b</p>"


def test_template_empty():
    assert render("<><p>before</p><Template></Template><p>after</p></>") == "<p>before</p><p>after</p>"


def test_template_if_true():
    assert render("<><Template if={{ condition }}><p>a</p><p>b</p></Template></>", condition=True) == "<p>a</p><p>b</p>"


def test_template_if_false():
    assert render("<><p>before</p><Template if={{ condition }}><p>a</p></Template><p>after</p></>", condition=False) == "<p>before</p><p>after</p>"


def test_template_for():
    result = render("<><dl><Template for={{ key, value in pairs }}><dt>{{ key }}</dt><dd>{{ value }}</dd></Template></dl></>", pairs=[("a", 1), ("b", 2)])
    assert result == "<dl><dt>a</dt><dd>1</dd><dt>b</dt><dd>2</dd></dl>"


def test_template_for_with_if():
    result = render("<><Template for={{ number in numbers }} if={{ number != 2 }}><i>{{ number }}</i>,</Template></>", numbers=[1, 2, 3])
    assert result == "<i>1</i>,<i>3</i>,"


def test_template_text_and_interpolation_children():
    assert render("<><Template for={{ name in names }}>Hi {{ name }}. </Template></>", names=["a", "b"]) == "Hi a. Hi b. "


def test_template_nested_guard_around_loop():
    source = "<><Template if={{ show }}><Template for={{ item in items }}><li>{{ item }}</li></Template></Template></>"
    assert render(source, show=True, items=["x", "y"]) == "<li>x</li><li>y</li>"
    assert render(source, show=False, items=["x", "y"]) == ""


def test_template_inside_component_children():
    def Wrapper(children: str) -> str:
        return f"<section>{children}</section>"

    result = render("<><Wrapper><Template for={{ item in items }}><p>{{ item }}</p></Template></Wrapper></>", Wrapper=Wrapper, items=["x", "y"])
    assert result == "<section><p>x</p><p>y</p></section>"


# ---------------------------------------------------------------------------
# Components
# ---------------------------------------------------------------------------


def test_void_component():
    def Badge(label: str) -> str:
        return f"<span>{label}</span>"

    result = render('<><Badge label="hi" /></>', Badge=Badge)
    assert result == "<span>hi</span>"


def test_component_no_children():
    def Badge(children: str, label: str) -> str:
        return f"<h1>{label}</h1><span>{children}</span>"

    result = render('<><Badge label="hi"></Badge></>', Badge=Badge)
    assert result == "<h1>hi</h1><span></span>"


def test_component_with_children():
    from fragments.types import Children

    def Wrapper(children: Children) -> str:
        return f"<div>{children}</div>"

    result = render("<><Wrapper><p>content</p></Wrapper></>", Wrapper=Wrapper)
    assert result == "<div><p>content</p></div>"


def test_component_children_pre_joined():
    from fragments.types import Children

    def Wrapper(children: Children) -> str:
        return f"<div>{children}</div>"

    result = render(
        "<><Wrapper><p>one</p><p>two</p></Wrapper></>",
        Wrapper=Wrapper,
    )
    assert result == "<div><p>one</p><p>two</p></div>"


# ---------------------------------------------------------------------------
# Special attributes — className and style
# ---------------------------------------------------------------------------


def test_interpolated_classname_list():
    result = render("<><div className={{ classes }}>text</div></>", classes=["foo", "bar"])
    assert result == '<div class="foo bar">text</div>'


def test_interpolated_classname_string():
    result = render("<><div className={{ classes }}>text</div></>", classes="foo bar")
    assert result == '<div class="foo bar">text</div>'


def test_interpolated_style_dict():
    result = render("<><div style={{ styles }}>text</div></>", styles={"color": "red", "font-size": "12px"})
    assert result == '<div style="color: red;font-size: 12px">text</div>'


def test_interpolated_style_string():
    result = render("<><div style={{ styles }}>text</div></>", styles="color: red")
    assert result == '<div style="color: red">text</div>'


# ---------------------------------------------------------------------------
# Boolean attributes
# ---------------------------------------------------------------------------


def test_bare_boolean_attribute():
    assert render("<><input disabled /></>") == "<input disabled />"


def test_bare_boolean_attribute_with_regular_attribute():
    result = render('<><input type="checkbox" checked /></>')
    assert result == '<input type="checkbox" checked />'


def test_multiple_bare_boolean_attributes():
    assert render("<><input disabled required /></>") == "<input disabled required />"


def test_boolean_attribute_none_value():
    assert render("<><input disabled={{ None }} /></>") == "<input  />"


def test_boolean_attribute_true_value():
    assert render("<><input disabled={{ True }} /></>") == '<input disabled="true" />'


def test_boolean_attribute_false_value():
    assert render("<><input disabled={{ False }} /></>") == '<input disabled="false" />'


def test_boolean_attribute_true_or_none_value():
    assert render("<><input disabled={{ True or None }} /></>") == '<input disabled="true" />'


def test_boolean_attribute_false_or_none_value():
    assert render("<><input disabled={{ False or None }} /></>") == "<input  />"


# ---------------------------------------------------------------------------
# Text escaping
# ---------------------------------------------------------------------------


def test_text_with_double_quotes():
    assert render('<><p>He said "hi"</p></>') == '<p>He said "hi"</p>'


def test_text_with_backslash():
    assert render(r"<><p>C:\temp</p></>") == r"<p>C:\temp</p>"


def test_comment_with_double_quotes():
    assert render('<><!-- "quoted" --></>') == '<!--  "quoted"  -->'


# ---------------------------------------------------------------------------
# Scripts and styles
# ---------------------------------------------------------------------------


def test_script_body_is_verbatim():
    body = r"""
    if (a < b && c > d) { console.log("x\n", '{{ y }}', `</>`); }
"""
    assert render(f"<><script>{body}</script></>") == f"<script>{body}</script>"


def test_style_body_is_verbatim():
    body = "\n    .card > h2 { content: \"\\201C\"; }\n"
    assert render(f"<><style>{body}</style></>") == f"<style>{body}</style>"


def test_script_with_interpolated_attribute():
    assert render("<><script nonce={{ nonce }}>run()</script></>", nonce="abc") == '<script nonce="abc">run()</script>'


def test_script_if_false():
    assert render("<><script if={{ False }}>run()</script></>") == ""


def test_script_self_closing_is_transpiled_as_written():
    assert render('<><script src="app.js" /></>') == '<script src="app.js" />'


def test_script_closing_tag_whitespace():
    assert render("<><script>run()</script ></>") == "<script>run()</script>"
