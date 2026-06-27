# HTML Library

The transpiler generates f-strings directly for HTML elements, and imports two runtime helpers from `fragments.html.elements` for the cases that need them.

**`attribute_to_string(name, value)`** renders a single HTML attribute. It is called inside f-string interpolations in the transpiled code whenever an attribute has a dynamic value.

| Argument | Type | Purpose |
|---|---|---|
| `name` | `str` | The attribute name |
| `value` | `Any` | The attribute value |

All values are HTML-escaped before being inserted into the attribute string, so characters like `"`, `&`, `<`, and `>` in dynamic values are always safe.

Special cases handled automatically:

- `className` — converted to `class="..."`. Accepts a string or a list of strings (joined with spaces).
- `style` — converted to `style="..."`. Accepts a string or a dict of CSS properties.
- `None` — omits the attribute entirely.
- `dict` or `list` — JSON-encoded.

**`comment(content)`** renders an HTML comment — it is what `<!-- ... -->` compiles to.
