import json
from typing import Any
from fragments.types import Children


def sequence(children: Children) -> str:
    return "".join(str(child) for child in children)


def el(
    name: str,
    children: Children,
    oneline: bool,
    attributes: dict[str, Any],
) -> str:
    tag_contents = [
        name,
        classes_to_string(attributes.pop("classes")) if "classes" in attributes else None,
        style_to_string(attributes.pop("style")) if "style" in attributes else None,
        attributes_to_string(attributes) if attributes is not None else None,
    ]
    tag_contents = [item for item in tag_contents if item is not None]
    tag_contents_string = " ".join(tag_contents)

    if oneline:
        return f"""<{tag_contents_string} />"""

    children_string = sequence(children)

    return f"""<{tag_contents_string}>{children_string}</{name}>"""


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
        value = json.dumps(value)

    if isinstance(value, bool):
        value = str(value).lower()

    return f'{name}="{value}"'


def classes_to_string(classes: list[str] | str) -> str:
    if isinstance(classes, list):
        inner = " ".join(classes)
    else:
        inner = classes

    return f'class="{inner}"'


def style_to_string(style: dict[str, str] | str) -> str:
    if isinstance(style, dict):
        inner = ";".join(": ".join(pair) for pair in style.items())
    else:
        inner = style

    return f'style="{inner}"'
