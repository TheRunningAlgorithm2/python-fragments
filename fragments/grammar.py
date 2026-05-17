from re import Match
import re

from fragments.ast_nodes import ASTFragment, ASTHTMLAttribute, ASTHTMLElement, ASTHTMLText, ASTInterpolation, ASTModule, ASTPython
from fragments.source import Source

WHITESPACE = r"\s*"
PYTHON = r"([\s\S]*?)(?=<>)|[\s\S]*$"
IDENTIFIER = r"[a-zA-Z_][a-zA-Z0-9_]*"
STRING_CONTENTS = r"(.*?)(?=\")"
INTERPOLATION_EXPRESSION = r"(.*?)(?= }})"
HTML_IDENTIFIER = r"[a-zA-Z][a-zA-Z0-9_-]*"
HTML_TEXT = r"(.*?)(?=<)"


class ParsingError(Exception): ...


def optional_regex(source: Source, pattern: str) -> tuple[Source, str | None]:
    """Expect the source to start with the given pattern, return the source after the pattern and the found match (if any)."""
    result: Match[str] | None = re.match(pattern, source.remaining())
    if result is None:
        return source, None
    return source.eat(result.end()), result.group(0)


def expect_regex(source: Source, pattern: str, label: str) -> tuple[Source, str]:
    """Expect the source to start with the given pattern, return the source after the pattern and the found match."""
    source, result = optional_regex(source, pattern)
    if result is None:
        raise ParsingError(f"Expected {label} but got {source.remaining()[:100]}...")
    return source, result


def expect_string(source: Source, string: str) -> Source:
    """Expect the source to start with the given string, return the source after the string."""
    if not source.remaining().startswith(string):
        raise ParsingError(f"Expected {string} but got {source.remaining()[:25]}...")
    return source.eat(len(string))


def expect_module(source: Source) -> tuple[Source, ASTModule]:
    """The top level of the recursive descent grammar."""
    children: list["ASTPython | ASTFragment"] = []
    source_start: int = source.offset
    while not source.at_end():
        if source.remaining().startswith("<>"):
            source, fragment = expect_fragment(source)
            children.append(fragment)
        else:
            source, python = expect_python(source)
            children.append(python)
    return source, ASTModule(source_start, source.offset, children)


def expect_python(source: Source) -> tuple[Source, ASTPython]:
    """Vanilla Python code."""
    source_start: int = source.offset
    source, python = expect_regex(source, PYTHON, "python source")
    return source, ASTPython(source_start, source.offset, python)


def expect_fragment(source: Source) -> tuple[Source, ASTFragment]:
    """A fragment - the top level of things created by this library."""
    source_start: int = source.offset
    source = expect_string(source, "<>")

    children: list[ASTHTMLElement | ASTHTMLText | ASTInterpolation] = []
    while not source.remaining().startswith("</>"):
        source, _ = optional_regex(source, WHITESPACE)
        if source.remaining().startswith("</>"):
            break
        source, child = expect_expression(source)
        children.append(child)

    source, _ = optional_regex(source, WHITESPACE)
    source = expect_string(source, "</>")
    source_end: int = source.offset

    return source, ASTFragment(source_start, source_end, children)


def expect_expression(source: Source) -> tuple[Source, ASTHTMLElement | ASTHTMLText | ASTInterpolation]:
    """Any HTML / functional block that might appear as part of the fragment."""
    if source.remaining().startswith("<"):
        source, html_element = expect_html_element(source)
        return source, html_element

    if source.remaining().startswith("{{"):
        source, interpolation = expect_interpolation(source)
        return source, interpolation

    source, html_text = expect_html_text(source)
    return source, html_text


def expect_html_element(source: Source) -> tuple[Source, ASTHTMLElement]:
    """An HTML element that may appear in the fragment tree."""
    element_source_start = source.offset
    source = expect_string(source, "<")
    source, _ = optional_regex(source, WHITESPACE)
    source, name = expect_regex(source, HTML_IDENTIFIER, "element name")
    source, _ = optional_regex(source, WHITESPACE)

    attributes: dict[str, ASTHTMLAttribute] = {}
    while not (source.remaining().startswith(">") or source.remaining().startswith("/>")):
        attribute_source_start = source.offset
        source, attribute_name = expect_regex(source, HTML_IDENTIFIER, "attribute name")
        if not source.remaining().startswith("="):
            attribute = ASTHTMLAttribute(attribute_source_start, source.offset, attribute_name, None, None)
            attributes[attribute_name] = attribute
            continue
        source = expect_string(source, "=")

        if source.remaining().startswith('"'):
            source = expect_string(source, '"')
            source, attribute_value = expect_regex(source, STRING_CONTENTS, "attribute value")
            source = expect_string(source, '"')
            attribute = ASTHTMLAttribute(attribute_source_start, source.offset, attribute_name, attribute_value, None)
            attributes[attribute_name] = attribute
        elif source.remaining().startswith("{{ "):
            source, interpolation = expect_interpolation(source)
            attribute = ASTHTMLAttribute(attribute_source_start, source.offset, attribute_name, None, interpolation)
            attributes[attribute_name] = attribute

        source, _ = optional_regex(source, WHITESPACE)

    if_attribute = attributes.pop("if") if "if" in attributes else None
    for_attribute = attributes.pop("for") if "for" in attributes else None

    if source.remaining().startswith("/>"):
        source = expect_string(source, "/>")
        html_element = ASTHTMLElement(
            element_source_start,
            source.offset,
            name,
            attributes,
            if_attribute.interpolation if if_attribute is not None else None,
            for_attribute.interpolation if for_attribute is not None else None,
            [],
            True,
        )
        return source, html_element

    source = expect_string(source, ">")
    source, _ = optional_regex(source, WHITESPACE)

    children: list[ASTHTMLElement | ASTHTMLText | ASTInterpolation] = []
    while not source.remaining().startswith("</"):
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

    html_element = ASTHTMLElement(
        element_source_start,
        source.offset,
        name,
        attributes,
        if_attribute.interpolation if if_attribute is not None else None,
        for_attribute.interpolation if for_attribute is not None else None,
        children,
        False,
    )
    return source, html_element


def expect_interpolation(source: Source) -> tuple[Source, ASTInterpolation]:
    """An interpolation block."""
    source_start = source.offset
    source = expect_string(source, "{{")
    source, _ = optional_regex(source, WHITESPACE)
    source, expression = expect_regex(source, INTERPOLATION_EXPRESSION, "expression")
    source, _ = optional_regex(source, WHITESPACE)
    source = expect_string(source, "}}")
    return source, ASTInterpolation(source_start, source.offset, expression)


def expect_html_text(source: Source) -> tuple[Source, ASTHTMLText]:
    """Text as the child of an HTML expression."""
    source_start = source.offset
    source, text = expect_regex(source, HTML_TEXT, "text")
    return source, ASTHTMLText(source_start, source.offset, text)
