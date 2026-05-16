# How the Transpiler Works

Python does not natively understand `<>` or HTML tags inside `.py` files. Fragments solves this with a **source-level transpiler** that converts fragment syntax into plain Python at import time - so there is no build step.

## The import hook

When you import `fragments.loader`, it installs a custom `MetaPathFinder` on `sys.meta_path`. From that point on, every `.py` file that Python imports is intercepted. If the file contains `<>`, the source is transpiled before it reaches the interpreter. Files without `<>` pass through unchanged.

```python
from fragments import loader  # installs the hook — must come first

from fastapi import FastAPI   # any fragment-containing module imported after
from routes import router     # this line is now transpiled automatically
```

The hook operates on source text, so nothing is written to disk — your `.py` files are never modified.

## A simple example

**Source code**

```python
from fragments import loader  # isort: skip

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return <>
        <h1>Hello, world!</h1>
        <p>Welcome to Fragments.</p>
    </>
```

**After transpilation — what the interpreter sees:**

```python
from fragments.html.elements import el, sequence
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return sequence([el("h1", ["Hello, world!"], {}, False),el("p", ["Welcome to Fragments."], {}, False)])
```

**Endpoint return value** - A plain Python string

```python
'<h1>Hello, world!</h1><p>Welcome to Fragments.</p>'
```

The transpiler does two things:

1. Prepends `from fragments.html.elements import el, sequence` at the top of the file.
2. Replaces every `<> ... </>` block with a call to `sequence(...)`.

## The runtime functions

Fragments are translated into runtime functions from our HTML library `fragments.html`, this is how our native HTML awareness works:

**`el(name, children, attributes, oneline)`** builds a single HTML element.

| Argument | Type | Purpose |
|---|---|---|
| `name` | `str` | The tag name (`"h1"`, `"div"`, …) |
| `children` | `list[str]` | Rendered inner content |
| `attributes` | `dict[str, Any]` | HTML attributes |
| `oneline` | `bool` | `True` for self-closing tags (`/>`) |

**`sequence(children)`** concatenates a list of rendered strings into one — it is what `<> ... </>` compiles to at the top level.

For the simple example above, at runtime `el("h1", ["Hello, world!"], {}, False)` produces the string `<h1>Hello, world!</h1>`, and `sequence([...])` joins both elements into the final HTML response.

## Dynamic content — `for` and `if`

The `for` attribute on an element compiles to a **list comprehension**, and `sequence(...)` wraps it so the result is still a flat string.

**Before:**

```python
@app.get("/posts", response_class=HTMLResponse)
async def post_list() -> str:
    posts = get_posts()
    return <>
        <h1>Posts</h1>
        <article for={{ post in posts }}>
            <h2>{{ post.title }}</h2>
            <p>{{ post.summary }}</p>
        </article>
    </>
```

**After:**

```python
@app.get("/posts", response_class=HTMLResponse)
async def post_list() -> str:
    posts = get_posts()
    return sequence([el("h1", ["Posts"], {}, False),sequence([el("article", [el("h2", [post.title], {}, False),el("p", [post.summary], {}, False)], {}, False) for post in posts])])
```

**Result** (with two posts in the list):

```python
'<h1>Posts</h1><article><h2>First Post</h2><p>A short summary.</p></article><article><h2>Second Post</h2><p>Another summary.</p></article>'
```

The `for={{ post in posts }}` attribute is stripped from the element and becomes the `for post in posts` clause of a list comprehension. `sequence([... for post in posts])` then joins the resulting list of rendered articles.

Similarly, `if={{ condition }}` compiles to a Python ternary: `el(...) if condition else ''`.

## Components — uppercase tags

A tag whose name starts with an uppercase letter is treated as a **component call** rather than an HTML element. The tag name is used directly as a function reference, and the element's children and attributes are passed as the first two arguments.

**Before:**

```python
return <>
    <Layout title="My Blog">
        <h1>Posts</h1>
        <PostCard for={{ post in posts }} post={{ post }} />
    </Layout>
</>
```

**After:**

```python
return sequence([Layout([el("h1", ["Posts"], {}, False),sequence([PostCard([], {"post": post}) for post in posts])], {"title": "My Blog"})])
```

`Layout(children, attributes)` and `PostCard(children, attributes)` are ordinary Python functions — the transpiler just calls them. This means components get full type checking, refactoring support, and IDE completions with no extra tooling.
