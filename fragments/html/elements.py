from typing import Any


def sequence(children: list[str]) -> str:
    return "".join(children)


def el(
    name: str,
    children: list[str],
    attributes: dict[str, Any],
    oneline: bool,
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

    children_string = "".join(children)

    return f"""<{tag_contents_string}>{children_string}</{name}>"""


def attributes_to_string(attributes: dict[str, Any]) -> str:
    return " ".join("=".join([key, f'"{value}"']) if value is not None else key for key, value in attributes.items())


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
