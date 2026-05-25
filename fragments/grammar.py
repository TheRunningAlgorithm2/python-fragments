from re import Match
import re

from fragments.ast_nodes import (
    ASTComponent,
    ASTComponentArgument,
    ASTControlNode,
    ASTFragment,
    ASTHTMLAttribute,
    ASTHTMLComment,
    ASTHTMLElement,
    ASTHTMLText,
    ASTInterpolation,
    ASTModule,
    ASTPython,
    ASTHTMLChild,
)
from fragments.source import Source

IDENTIFIER = r"[a-zA-Z_][a-zA-Z0-9_]*"
HTML_IDENTIFIER = r"[a-zA-Z][a-zA-Z0-9_:.-]*"
HTML_TEXT = r"(.*?)(?=<|{{)"


class ParsingError(Exception):
    def __init__(self, message: str, source_start: int) -> None:
        super().__init__(message)
        self.source_start: int = source_start


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
        raise ParsingError(f"Expected {label}", source.offset)
    return source, result


def expect_string(source: Source, string: str) -> Source:
    """Expect the source to start with the given string, return the source after the string."""
    if not source.remaining().startswith(string):
        raise ParsingError(f"Expected {string}", source.offset)
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
    PYTHON = r"([\s\S]*?)(?=<>|'''|\"\"\"|'|\"|#)|[\s\S]*$"
    source_start: int = source.offset
    python: str = ""

    while not source.remaining().startswith("<>") and not source.at_end():
        source, next_python = expect_regex(source, PYTHON, "python source")
        python += next_python
        if source.remaining().startswith('"""'):
            source, next_python = expect_regex(source, r'"""([\s\S]*?)(?:"""|$)', "python source")
            python += next_python
        elif source.remaining().startswith("'''"):
            source, next_python = expect_regex(source, r"'''([\s\S]*?)(?:'''|$)", "python source")
            python += next_python
        elif source.remaining().startswith("'"):
            source, next_python = expect_regex(source, r"'(?:[^'\\]|\\.)*(?:'|$)", "python source")
            python += next_python
        elif source.remaining().startswith('"'):
            source, next_python = expect_regex(source, r'"(?:[^"\\]|\\.)*(?:"|$)', "python source")
            python += next_python
        elif source.remaining().startswith("#"):
            source, next_python = expect_regex(source, r"#[^\n]*", "python source")
            python += next_python

    return source, ASTPython(source_start, source.offset, python)


def expect_fragment(source: Source) -> tuple[Source, ASTFragment]:
    """A fragment - the top level of things created by this library."""
    source_start: int = source.offset
    source = expect_string(source, "<>")

    children: list[ASTHTMLChild] = []
    while not source.remaining().startswith("</>"):
        source, _ = source.eat_whitespace()
        if source.remaining().startswith("</>"):
            break
        source, child = expect_child(source)
        children.append(child)

    source, _ = source.eat_whitespace()
    source = expect_string(source, "</>")
    source_end: int = source.offset

    return source, ASTFragment(source_start, source_end, children)


def expect_child(source: Source) -> tuple[Source, ASTHTMLChild]:
    """Any HTML / functional block that might appear as part of the fragment."""
    if source.remaining().startswith("<!--"):
        source, html_comment = expect_html_comment(source)
        return source, html_comment

    if source.start_matches(r"<[A-Z]"):
        source, component = expect_component(source)
        return source, component

    if source.starts_with("<"):
        source, html_element = expect_html_element(source)
        return source, html_element

    if source.remaining().startswith("{{"):
        source, interpolation = expect_interpolation(source)
        return source, interpolation

    source, html_text = expect_html_text(source)
    return source, html_text


def expect_component(source: Source) -> tuple[Source, ASTComponent | ASTControlNode[ASTComponent]]:
    """An pseudo-element that actually resolves into a user-defined function call."""
    source_start = source.offset
    source = expect_string(source, "<")
    source, name = expect_regex(source, r"[A-Z][a-zA-Z0-9_]*", "component name")
    source, _ = source.eat_whitespace()

    arguments: dict[str, ASTComponentArgument] = {}
    while not source.starts_with(">") and not source.starts_with("/>"):
        argument_source_start = source.offset
        source, argument_name = expect_regex(source, r"[a-zA-Z][a-zA-Z0-9_]*", "python argument name")
        source = expect_string(source, "=")
        string_literal, interpolation = None, None
        if source.start_matches("['\"]"):
            source, string_literal = expect_string_literal(source)
        elif source.starts_with("{{"):
            source, interpolation = expect_interpolation(source)
        arguments[argument_name] = ASTComponentArgument(argument_source_start, source.offset, argument_name, string_literal, interpolation)
        source, _ = source.eat_whitespace()

    if_argument = arguments.pop("if") if "if" in arguments else None
    for_argument = arguments.pop("for") if "for" in arguments else None

    if source.starts_with("/>"):
        source = expect_string(source, "/>")
        return source, ASTControlNode[ASTComponent].wrap_child(
            ASTComponent(source_start, source.offset, name, arguments, []),
            if_argument.interpolation if if_argument is not None else None,
            for_argument.interpolation if for_argument is not None else None,
        )

    source = expect_string(source, ">")
    source, children = expect_children(source)
    source = expect_string(source, "</")
    source, closing_name = expect_regex(source, r"[A-Z][a-zA-Z0-9_]*", "component name")
    source, _ = source.eat_whitespace()
    source = expect_string(source, ">")

    if name != closing_name:
        raise ParsingError(f"Element closed ({closing_name!r}) is not the same as currently opened element ({name!r})", source.offset)

    return source, ASTControlNode[ASTComponent].wrap_child(
        ASTComponent(source_start=source_start, source_end=source.offset, name=name, arguments=arguments, children=children),
        if_argument.interpolation if if_argument is not None else None,
        for_argument.interpolation if for_argument is not None else None,
    )


def expect_html_comment(source: Source) -> tuple[Source, ASTHTMLComment]:
    source_start = source.offset
    source = expect_string(source, "<!--")
    source, content = expect_regex(source, r"[\s\S]*?(?=-->)", "comment content")
    source = expect_string(source, "-->")
    return source, ASTHTMLComment(source_start, source.offset, content)


def expect_html_element(source: Source) -> tuple[Source, ASTHTMLElement | ASTControlNode[ASTHTMLElement]]:
    """An HTML element that may appear in the fragment tree."""
    element_source_start = source.offset
    source = expect_string(source, "<")
    source, _ = source.eat_whitespace()
    source, name = expect_regex(source, HTML_IDENTIFIER, "element name")
    source, _ = source.eat_whitespace()

    attributes: dict[str, ASTHTMLAttribute] = {}
    while not (source.remaining().startswith(">") or source.remaining().startswith("/>")):
        attribute_source_start = source.offset
        source, attribute_name = expect_regex(source, HTML_IDENTIFIER, "attribute name")
        if not source.remaining().startswith("="):
            attribute = ASTHTMLAttribute(attribute_source_start, source.offset, attribute_name, None, None)
            attributes[attribute_name] = attribute
            source, _ = source.eat_whitespace()
            continue
        source = expect_string(source, "=")

        if source.remaining().startswith('"'):
            source, string_literal = expect_string_literal(source)
            attribute = ASTHTMLAttribute(attribute_source_start, source.offset, attribute_name, string_literal, None)
            attributes[attribute_name] = attribute
        elif source.remaining().startswith("{{"):
            source, interpolation = expect_interpolation(source)
            attribute = ASTHTMLAttribute(attribute_source_start, source.offset, attribute_name, None, interpolation)
            attributes[attribute_name] = attribute

        source, _ = source.eat_whitespace()

    if_attribute = attributes.pop("if") if "if" in attributes else None
    for_attribute = attributes.pop("for") if "for" in attributes else None

    if source.remaining().startswith("/>"):
        source = expect_string(source, "/>")
        html_element = ASTControlNode[ASTHTMLElement].wrap_child(
            ASTHTMLElement(element_source_start, source.offset, name, attributes, [], True),
            if_attribute.interpolation if if_attribute is not None else None,
            for_attribute.interpolation if for_attribute is not None else None,
        )
        return source, html_element

    source = expect_string(source, ">")
    source, _ = source.eat_whitespace()
    source, children = expect_children(source)
    source = expect_string(source, "</")
    source, _ = source.eat_whitespace()
    source, closing_name = expect_regex(source, IDENTIFIER, "element name")

    if name != closing_name:
        raise ParsingError(f"Element closed ({closing_name!r}) is not the same as currently opened element ({name!r})", source.offset)

    source, _ = source.eat_whitespace()
    source = expect_string(source, ">")

    html_element = ASTControlNode[ASTHTMLElement].wrap_child(
        ASTHTMLElement(element_source_start, source.offset, name, attributes, children, False),
        if_attribute.interpolation if if_attribute is not None else None,
        for_attribute.interpolation if for_attribute is not None else None,
    )
    return source, html_element


def expect_children(source: Source) -> tuple[Source, list[ASTHTMLChild]]:
    children: list[ASTHTMLChild] = []
    source, _ = source.eat_whitespace()
    while not source.remaining().startswith("</"):
        source, child = expect_child(source)
        children.append(child)
        source, _ = source.eat_whitespace()
    return source, children


def expect_interpolation(source: Source) -> tuple[Source, ASTInterpolation]:
    """An interpolation block."""
    INTERPOLATION_EXPRESSION = r"([\s\S]*?)(?= }})"
    source_start = source.offset
    source = expect_string(source, "{{")
    source, leading_whitespace = source.eat_whitespace()
    source, expression = expect_regex(source, INTERPOLATION_EXPRESSION, "expression")
    source, trailing_whitespace = source.eat_whitespace()
    source = expect_string(source, "}}")
    return source, ASTInterpolation(source_start, source.offset, expression, len(leading_whitespace), len(trailing_whitespace))


def expect_html_text(source: Source) -> tuple[Source, ASTHTMLText]:
    """Text as the child of an HTML expression."""
    source_start = source.offset
    source, text = expect_regex(source, HTML_TEXT, "text")
    return source, ASTHTMLText(source_start, source.offset, text)


def expect_string_literal(source: Source) -> tuple[Source, str]:
    return expect_regex(source, r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'', "string literal")
