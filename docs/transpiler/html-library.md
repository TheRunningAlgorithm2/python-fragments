# HTML Library

Fragments are translated into calls to two runtime functions from `fragments.html.elements`. This is what gives Fragments native HTML awareness.

**`el(name, children, oneline, **attributes)`** builds a single HTML element.

| Argument | Type | Purpose |
|---|---|---|
| `name` | `str` | The tag name (`"h1"`, `"div"`, …) |
| `children` | `list[str]` | Rendered inner content |
| `oneline` | `bool` | `True` for self-closing tags (`/>`) |
| `**attributes` | `Any` | HTML attributes passed as keyword arguments |

**`sequence(children)`** concatenates a list of rendered strings into one — it is what `<> ... </>` compiles to at the top level.

For example, `el("h1",["Hello, world!"],oneline=False,)` produces the string `<h1>Hello, world!</h1>`, and `sequence([...])` joins a list of elements into the final HTML string.
