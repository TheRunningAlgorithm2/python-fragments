from fragments.grammar import expect_module
from fragments.source import Source


def render(source_str: str, **variables: object) -> str:
    """Transpile a fragment source string, execute it, and return the result."""
    source = Source.from_string(f"result = {source_str.strip()}")
    _, module = expect_module(source)
    module.transpile(0)
    namespace: dict[str, object] = dict(variables)
    exec(module.transpiled_content, namespace)
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
    assert render('<></>') == ""


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
# Components
# ---------------------------------------------------------------------------


def test_component_no_children():
    def Badge(children: str, label: str) -> str:
        return f"<span>{label}</span>"

    result = render("<><Badge label=\"hi\" /></>", Badge=Badge)
    assert result == "<span>hi</span>"


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
