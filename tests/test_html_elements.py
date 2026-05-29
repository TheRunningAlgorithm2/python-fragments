from fragments.html.elements import el, className_to_string


def test_className_list_joined_with_spaces():
    result = className_to_string(["foo", "bar", "baz"])
    assert result == 'class="foo bar baz"'


def test_className_empty_list():
    result = className_to_string([])
    assert result == 'class=""'


def test_className_single_item_list():
    result = className_to_string(["only"])
    assert result == 'class="only"'


def test_className_string_passthrough():
    result = className_to_string("already-a-string")
    assert result == 'class="already-a-string"'


def test_el_className_list_attribute():
    result = el("div", ["content"], False, {"className": ["foo", "bar"]})
    assert result == '<div class="foo bar">content</div>'


def test_el_className_empty_list():
    result = el("div", [], True, {"className": []})
    assert result == '<div class="" />'
