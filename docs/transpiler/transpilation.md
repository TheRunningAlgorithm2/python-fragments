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
from fragments.html.elements import attribute_to_string, comment
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return f"<h1>"+"Hello, world!"+"</h1>"+f"<p>"+"Welcome to Fragments."+"</p>"
```

**Endpoint return value** — a plain Python string:

```python
'<h1>Hello, world!</h1><p>Welcome to Fragments.</p>'
```

The transpiler does two things:

1. Prepends `from fragments.html.elements import attribute_to_string, comment` at the top of the file.
2. Replaces every `<> ... </>` block with its children joined by `+`.

## Dynamic content — `for` and `if`

The `for` attribute on an element compiles to a **generator expression** wrapped in `''.join(str(...) for ...)` so the result is a flat string.

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
    return f"<h1>"+"Posts"+"</h1>"+''.join(str(f"<article>"+f"<h2>"+post.title+"</h2>"+f"<p>"+post.summary+"</p>"+"</article>") for post in posts)
```

**Result** (with two posts in the list):

```python
'<h1>Posts</h1><article><h2>First Post</h2><p>A short summary.</p></article><article><h2>Second Post</h2><p>Another summary.</p></article>'
```

The `for={{ post in posts }}` attribute is stripped from the element and becomes the `for post in posts` clause of a generator expression. `''.join(str(...) for post in posts)` then joins the resulting rendered articles into a flat string.

Similarly, `if={{ condition }}` compiles to a Python ternary: `(element if condition else '')`.

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
return Layout(children=""+f"<h1>"+"Posts"+"</h1>"+''.join(str(PostCard(post=post)) for post in posts),title="My Blog")
```

`Layout` and `PostCard` are ordinary Python functions. The transpiler passes children as a keyword argument named `children` (a pre-joined string) and tag attributes as additional keyword arguments. Self-closing components receive no `children` argument at all. How kwargs are received is up to the component:

```python
from fragments.types import Children

# Components that receive children declare a children parameter
def Layout(children: Children, **kwargs: Any) -> str: ...
def Card(children: Children, classes: str = "") -> str: ...

# Self-closing components need no children parameter
def PostCard(post: Post) -> str: ...
```

Explicit parameters give you full type checking, refactoring support, and IDE completions with no extra tooling.
