import json
from typing import Any
import html


def comment(content: str) -> str:
    return f"<!-- {content} -->"


def attribute_to_string(name: str, value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, tuple):
        value = list(value)

    if name == "className":
        return className_to_string(value)

    if name == "style":
        return style_to_string(value)

    if isinstance(value, dict) or isinstance(value, list):
        value = json.dumps(value)

    if isinstance(value, bool):
        value = str(value).lower()

    return f'{name}="{html.escape(str(value))}"'


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
