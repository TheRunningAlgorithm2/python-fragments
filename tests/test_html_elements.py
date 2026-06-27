from fragments.html.elements import attribute_to_string, className_to_string


def test_attribute_plain_string():
    assert attribute_to_string("href", "/path") == 'href="/path"'


def test_attribute_string_escapes_double_quote():
    assert attribute_to_string("data-value", 'say "hello"') == 'data-value="say &quot;hello&quot;"'


def test_attribute_string_escapes_ampersand():
    assert attribute_to_string("title", "cats & dogs") == 'title="cats &amp; dogs"'


def test_attribute_string_escapes_arrow_in_expression():
    assert attribute_to_string("x-on:click", "items.filter(item => item.active)") == (
        'x-on:click="items.filter(item =&gt; item.active)"'
    )


def test_attribute_dict_escapes_quotes_from_json():
    assert attribute_to_string("data-config", {"key": "value"}) == 'data-config="{&quot;key&quot;: &quot;value&quot;}"'


def test_attribute_bool_true():
    assert attribute_to_string("disabled", True) == 'disabled="true"'


def test_attribute_bool_false():
    assert attribute_to_string("disabled", False) == 'disabled="false"'


def test_attribute_none_returns_empty():
    assert attribute_to_string("hidden", None) == ""


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
