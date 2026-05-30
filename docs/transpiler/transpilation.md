# Transpilation

Python does not natively understand `<>` or HTML tags inside `.py` files. Fragments solves this with a **source-level transpiler** that converts fragment syntax into plain Python at import time — so there is no build step.

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
from fragments.html.elements import el, _sequence, comment
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return el("h1","Hello, world!",oneline=False,attributes={})+el("p","Welcome to Fragments.",oneline=False,attributes={})
```

**Endpoint return value** — a plain Python string:

```python
'<h1>Hello, world!</h1><p>Welcome to Fragments.</p>'
```

The transpiler does two things:

1. Prepends `from fragments.html.elements import el, _sequence, comment` at the top of the file.
2. Replaces every `<> ... </>` block with its children joined by `+`.

## Dynamic content — `for` and `if`

The `for` attribute on an element compiles to a **list comprehension**, and `_sequence(...)` wraps it so the result is still a flat string.

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
    return el("h1","Posts",oneline=False,attributes={})+_sequence([el("article",el("h2",post.title,oneline=False,attributes={})+el("p",post.summary,oneline=False,attributes={}),oneline=False,attributes={}) for post in posts])
```

**Result** (with two posts in the list):

```python
'<h1>Posts</h1><article><h2>First Post</h2><p>A short summary.</p></article><article><h2>Second Post</h2><p>Another summary.</p></article>'
```

The `for={{ post in posts }}` attribute is stripped from the element and becomes the `for post in posts` clause of a list comprehension. `_sequence([... for post in posts])` then joins the resulting list of rendered articles.

Similarly, `if={{ condition }}` compiles to a Python ternary: `(el(...) if condition else '')`.

## Components — uppercase tags

A tag whose name starts with an uppercase letter is treated as a **component call** rather than an HTML element. The tag name is used directly as a function reference, and the element's children and attributes are passed as arguments.

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
return Layout(el("h1","Posts",oneline=False,attributes={})+_sequence([PostCard("",post=post) for post in posts]),title="My Blog")
```

`Layout` and `PostCard` are ordinary Python functions — the transpiler calls them with children as the first positional argument (a pre-joined string) and tag attributes as keyword arguments. How those kwargs are received is up to the component:

```python
from fragments.types import Children

# Accept any attributes with **kwargs
def Layout(children: Children, **kwargs: Any) -> str: ...

# Or declare each attribute explicitly for type checking
def PostCard(children: Children, post: Post) -> str: ...
```

Explicit parameters give you full type checking, refactoring support, and IDE completions with no extra tooling.
