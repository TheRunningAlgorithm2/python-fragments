import re

from fragments.nodes import ASTFragment, ASTHTMLAttribute, ASTHTMLElement, ASTHTMLText, ASTInterpolation

WHITESPACE = r"\s*"

PYTHON = r"([\s\S]*?)(?=[ ]*<>)|[\s\S]*$"
IDENTIFIER = r"[a-zA-Z_][a-zA-Z0-9_]*"
STRING_CONTENTS = r"(.*?)(?=\")"
INTERPOLATION_EXPRESSION = r"(.*?)(?= }})"
HTML_IDENTIFIER = r"[a-zA-Z][a-zA-Z0-9_-]*"
HTML_TEXT = r"(.*?)(?=<)"


class ParsingError(Exception): ...


def optional_regex(source: str, pattern: str) -> tuple[str, str | None]:
    """Expect the source to start with the given pattern, return the source after the pattern and the found match (if any)."""
    result = re.match(pattern, source)
    if result is None:
        return source, None
    return source[result.end() :], result.group(0)


def expect_regex(source: str, pattern: str, label: str) -> tuple[str, str]:
    """Expect the source to start with the given pattern, return the source after the pattern and the found match."""
    source, result = optional_regex(source, pattern)
    if result is None:
        raise ParsingError(f"Expected {label} but got {source[:100]}...")
    return source, result


def expect_string(source: str, string: str) -> str:
    """Expect the source to start with the given string, return the source after the string."""
    if not source.startswith(string):
        raise ParsingError(f"Expected {string} but got {source[:25]}...")
    return source[len(string) :]


def expect_fragment(source: str) -> tuple[str, ASTFragment]:
    """The top level of the recursive descent grammar."""
    source = expect_string(source, "<>")

    children: list[ASTHTMLElement | ASTHTMLText | ASTInterpolation] = []
    while not source.startswith("</>"):
        source, _ = optional_regex(source, WHITESPACE)
        if source.startswith("</>"):
            break
        source, child = expect_expression(source)
        children.append(child)

    source, _ = optional_regex(source, WHITESPACE)
    source = expect_string(source, "</>")

    return source, ASTFragment(children)


def expect_expression(source: str) -> tuple[str, ASTHTMLElement | ASTHTMLText | ASTInterpolation]:
    """Any HTML / functional block that might appear as part of the fragment."""
    if source.startswith("<"):
        source, html_element = expect_html_element(source)
        return source, html_element

    if source.startswith("{{"):
        source, interpolation = expect_interpolation(source)
        return source, interpolation

    source, html_text = expect_html_text(source)
    return source, html_text


def expect_html_element(source: str) -> tuple[str, ASTHTMLElement]:
    """An HTML element that may appear in the fragment tree."""
    source = expect_string(source, "<")
    source, _ = optional_regex(source, WHITESPACE)
    source, name = expect_regex(source, HTML_IDENTIFIER, "element name")
    source, _ = optional_regex(source, WHITESPACE)

    attributes: dict[str, ASTHTMLAttribute] = {}
    while not (source.startswith(">") or source.startswith("/>")):
        source, attribute_name = expect_regex(source, HTML_IDENTIFIER, "attribute name")
        if not source.startswith("="):
            attribute = ASTHTMLAttribute(attribute_name, None, None)
            attributes[attribute_name] = attribute
            continue
        source = expect_string(source, "=")

        if source.startswith('"'):
            source = expect_string(source, '"')
            source, attribute_value = expect_regex(source, STRING_CONTENTS, "attribute value")
            source = expect_string(source, '"')
            attribute = ASTHTMLAttribute(attribute_name, attribute_value, None)
            attributes[attribute_name] = attribute
        elif source.startswith("{{ "):
            source, interpolation = expect_interpolation(source)
            attribute = ASTHTMLAttribute(attribute_name, None, interpolation)
            attributes[attribute_name] = attribute

        source, _ = optional_regex(source, WHITESPACE)

    if source.startswith("/>"):
        source = expect_string(source, "/>")
        html_element = ASTHTMLElement(name, attributes, [], True)
        return source, html_element

    source = expect_string(source, ">")
    source, _ = optional_regex(source, WHITESPACE)

    children = []
    while not source.startswith("</"):
        source, child = expect_expression(source)
        children.append(child)
        source, _ = optional_regex(source, WHITESPACE)

    source = expect_string(source, "</")
    source, _ = optional_regex(source, WHITESPACE)
    source, closing_name = expect_regex(source, IDENTIFIER, "element name")

    if name != closing_name:
        raise ValueError(f"Element closed ({closing_name!r}) is not the same as currently opened element ({name!r})")

    source, _ = optional_regex(source, WHITESPACE)
    source = expect_string(source, ">")

    html_element = ASTHTMLElement(name, attributes, children, False)
    return source, html_element


def expect_interpolation(source: str) -> tuple[str, ASTInterpolation]:
    """An interpolation block."""
    source = expect_string(source, "{{")
    source, _ = optional_regex(source, WHITESPACE)
    source, expression = expect_regex(source, INTERPOLATION_EXPRESSION, "expression")
    source, _ = optional_regex(source, WHITESPACE)
    source = expect_string(source, "}}")
    return source, ASTInterpolation(expression)


def expect_html_text(source: str) -> tuple[str, ASTHTMLText]:
    """Text as the child of an HTML expression."""
    source, text = expect_regex(source, HTML_TEXT, "text")
    return source, ASTHTMLText(text)
