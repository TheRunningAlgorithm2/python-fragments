import re

from fragments.nodes import ASTForBlock, ASTFragment, ASTHTMLAttribute, ASTHTMLElement, ASTHTMLText, ASTIfBlock, ASTInterpolation, ASTNode, ASTWhileBlock

WHITESPACE = r"\s*"

PYTHON = r"([\s\S]*?)(?=[ ]*return <>)|[\s\S]*$"
IDENTIFIER = r"[a-zA-Z_][a-zA-Z0-9_]*"
PARAM_LIST = r"(.*?)(?=\))"
FRAGMENT_BODY = r"([\s\S]*?)(?=return)"
STRING_CONTENTS = r"(.*?)(?=\")"
FOR_BLOCK_ITERATOR = r"(.*?)(?= in )"
FOR_BLOCK_ITERABLE = r"(.*?)(?= %})"
IF_CONDITION = r"(.*?)(?= %})"
WHILE_CONDITION = r"(.*?)(?= %})"
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
    source = expect_string(source, "return <>")
    source, _ = optional_regex(source, WHITESPACE)

    children: list[ASTNode] = []
    while not source.startswith("</>"):
        source, _ = optional_regex(source, WHITESPACE)
        if source.startswith("</>"):
            break
        source, child = expect_expression(source)
        children.append(child)

    source, _ = optional_regex(source, WHITESPACE)
    source = expect_string(source, "</>")

    return source, ASTFragment(children)


def expect_expression(source: str) -> tuple[str, ASTNode]:
    """Any HTML / functional block that might appear as part of the fragment."""
    if source.startswith("<"):
        source, html_element = expect_html_element(source)
        return source, html_element

    if source.startswith("{% for"):
        source, for_block = expect_for_block(source)
        return source, for_block

    if source.startswith("{% if"):
        source, if_block = expect_if_block(source)
        return source, if_block

    if source.startswith("{% while"):
        source, while_block = expect_while_block(source)
        return source, while_block

    if source.startswith("{{ "):
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

    attributes: list[ASTHTMLAttribute] = []
    while not (source.startswith(">") or source.startswith("/>")):
        source, attribute_name = expect_regex(source, HTML_IDENTIFIER, "attribute name")
        if not source.startswith("="):
            attribute = ASTHTMLAttribute(attribute_name, None, None)
            attributes.append(attribute)
            continue
        source = expect_string(source, "=")

        if source.startswith('"'):
            source = expect_string(source, '"')
            source, attribute_value = expect_regex(source, STRING_CONTENTS, "attribute value")
            source = expect_string(source, '"')
            attribute = ASTHTMLAttribute(attribute_name, attribute_value, None)
            attributes.append(attribute)
        elif source.startswith("{{ "):
            source, interpolation = expect_interpolation(source)
            attribute = ASTHTMLAttribute(attribute_name, None, interpolation)
            attributes.append(attribute)

        source, _ = optional_regex(source, WHITESPACE)

    if source.startswith("/>"):
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


def expect_for_block(source: str) -> tuple[str, ASTForBlock]:
    """A for-loop control block."""
    source = expect_string(source, "{% for ")
    source, iterator = expect_regex(source, FOR_BLOCK_ITERATOR, "for block iterator")
    source = expect_string(source, " in ")
    source, iterable = expect_regex(source, FOR_BLOCK_ITERABLE, "for block iterable")
    source = expect_string(source, " %}")

    source, _ = optional_regex(source, WHITESPACE)

    children = []
    while not source.startswith("{% endfor %}"):
        source, child = expect_expression(source)
        children.append(child)
        source, _ = optional_regex(source, WHITESPACE)

    source = expect_string(source, "{% endfor %}")

    return source, ASTForBlock(iterator, iterable, children)


def expect_if_block(source: str) -> tuple[str, ASTIfBlock]:
    """An "if" control block."""
    source = expect_string(source, "{% if ")
    source, condition = expect_regex(source, IF_CONDITION, "if condition")
    source = expect_string(source, " %}")

    source, _ = optional_regex(source, WHITESPACE)

    children = []
    while not source.startswith("{% endif %}"):
        source, child = expect_expression(source)
        children.append(child)
        source, _ = optional_regex(source, WHITESPACE)

    source = expect_string(source, "{% endif %}")

    if_block = ASTIfBlock(condition, children)
    return source, if_block


def expect_while_block(source: str) -> tuple[str, ASTWhileBlock]:
    """A while-loop control block."""
    source = expect_string(source, "{% while ")
    source, condition = expect_regex(source, WHILE_CONDITION, "while condition")
    source = expect_string(source, " %}")
    source, _ = optional_regex(source, WHITESPACE)

    children = []
    while not source.startswith("{% endwhile %}"):
        source, child = expect_expression(source)
        children.append(child)
        source, _ = optional_regex(source, WHITESPACE)

    source = expect_string(source, "{% endwhile %}")

    while_block = ASTWhileBlock(condition, children)
    return source, while_block


def expect_interpolation(source: str) -> tuple[str, ASTInterpolation]:
    """An interpolation block."""
    source = expect_string(source, "{{ ")
    source, expression = expect_regex(source, INTERPOLATION_EXPRESSION, "expression")
    source = expect_string(source, " }}")
    return source, ASTInterpolation(expression)


def expect_html_text(source: str) -> tuple[str, ASTHTMLText]:
    """Text as the child of an HTML expression."""
    source, text = expect_regex(source, HTML_TEXT, "text")
    return source, ASTHTMLText(text)
