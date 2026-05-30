import json
from typing import Any
from fragments.types import Children, Stringable
import html


def _sequence(items: list[str | Stringable]) -> str:
    return "".join(str(item) for item in items)


def el(
    name: str,
    children: Children,
    oneline: bool,
    attributes: dict[str, Any],
) -> str:
    tag_contents = [
        name,
        className_to_string(attributes.pop("className")) if "className" in attributes else None,
        style_to_string(attributes.pop("style")) if "style" in attributes else None,
        attributes_to_string(attributes) if attributes else None,
    ]
    tag_contents = [item for item in tag_contents if item is not None]
    tag_contents_string = " ".join(tag_contents)

    if oneline:
        return f"""<{tag_contents_string} />"""

    return f"""<{tag_contents_string}>{children}</{name}>"""


def comment(content: str) -> str:
    return f"<!-- {content} -->"


def attributes_to_string(attributes: dict[str, Any]) -> str:
    return " ".join(attribute_to_string(name, value) for name, value in attributes.items())


def attribute_to_string(name: str, value: Any) -> str:
    if value is None:
        return name

    if isinstance(value, tuple):
        value = list(value)

    if isinstance(value, dict) or isinstance(value, list):
        value = html.escape(json.dumps(value))

    if isinstance(value, bool):
        value = str(value).lower()

    return f'{name}="{value}"'


def className_to_string(contents: list[str] | str) -> str:
    if isinstance(contents, list):
        inner = " ".join(contents)
    else:
        inner = contents

    return f'class="{inner}"'


def style_to_string(style: dict[str, str] | str) -> str:
    if isinstance(style, dict):
        inner = ";".join(": ".join(pair) for pair in style.items())
    else:
        inner = style

    return f'style="{inner}"'
