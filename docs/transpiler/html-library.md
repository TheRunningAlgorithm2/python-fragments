# HTML Library

Fragments are translated into calls to runtime functions from `fragments.html.elements`. This is what gives Fragments native HTML awareness.

**`el(name, children, oneline, attributes)`** builds a single HTML element.

| Argument | Type | Purpose |
|---|---|---|
| `name` | `str` | The tag name (`"h1"`, `"div"`, …) |
| `children` | `Children` | Rendered inner content as a string |
| `oneline` | `bool` | `True` for self-closing tags (`/>`) |
| `attributes` | `dict[str, Any]` | HTML attributes as a dict |

**`comment(content)`** renders an HTML comment — it is what `<!-- ... -->` compiles to.

For example, `el("h1","Hello, world!",oneline=False,attributes={})` produces the string `<h1>Hello, world!</h1>`.

The `_sequence(items)` function is used internally by the transpiler to join list comprehensions (from `for` attributes) into strings. It is not part of the public API and should not be called directly.
