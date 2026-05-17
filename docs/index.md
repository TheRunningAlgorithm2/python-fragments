# Python Fragments

**Modern HTML template rendering in Python** - no build step, no template files, and native HTML awareness out of the box.

=== "Plain Python"

    ```python
    from fragments import loader  # isort: skip

    from my_components import Layout, PostCard

    POSTS = [...]  # your data here

    def render_index() -> str:
        published = [p for p in POSTS if p.published]
        return <>
            <Layout title="My Blog">
                <h1>Latest Posts</h1>
                <PostCard for={{ post in published }} post={{ post }} />
            </Layout>
        </>
    ```

=== "FastAPI"

    ```python
    from fragments import loader  # isort: skip

    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse

    app = FastAPI()

    POSTS = [...]  # your data here

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        published = [p for p in POSTS if p.published]
        return <>
            <Layout title="My Blog">
                <h1>Latest Posts</h1>
                <PostCard for={{ post in published }} post={{ post }} />
            </Layout>
        </>
    ```

=== "Flask"

    ```python
    from fragments import loader  # isort: skip

    from flask import Flask

    app = Flask(__name__)

    POSTS = [...]  # your data here

    @app.route("/")
    def index() -> str:
        published = [p for p in POSTS if p.published]
        return <>
            <Layout title="My Blog">
                <h1>Latest Posts</h1>
                <PostCard for={{ post in published }} post={{ post }} />
            </Layout>
        </>
    ```

=== "Django"

    ```python
    from fragments import loader  # isort: skip

    from django.http import HttpRequest, HttpResponse

    POSTS = [...]  # your data here

    def index(request: HttpRequest) -> HttpResponse:
        published = [p for p in POSTS if p.published]
        return HttpResponse(<>
            <Layout title="My Blog">
                <h1>Latest Posts</h1>
                <PostCard for={{ post in published }} post={{ post }} />
            </Layout>
        </>)
    ```

---

## Why Fragments?

<div class="feature-grid">
  <div class="feature-card">
    <strong>No build step</strong>
    <p>Transpiled automatically at import time. No CLI, no watchers, no separate compile phase.</p>
  </div>
  <div class="feature-card">
    <strong>Native HTML</strong>
    <p>Real tags, attributes, and structure. If you know HTML, you already know fragment syntax.</p>
  </div>
  <div class="feature-card">
    <strong>Full IDE support</strong>
    <p>Type checking, hover, completions, go-to-definition, rename, and semantic highlighting via a built-in language server and VS Code extension.</p>
  </div>
</div>

---

## Get Started

### 1. Install

```bash
pip install python-fragments
```

Register the loader at your app's entry point, before importing any modules that use fragments:

```python
from fragments import loader
from my_components import my_component
```

Any `.py` file containing `<>` is transpiled automatically — nothing else to configure.

[Full installation guide](getting-started/installation.md)

### 2. Use With Your IDE

Install the language server for inline type errors, completions, and hover docs:

```bash
pip install python-fragments[lsp]
```

A **VS Code extension** is included with structural syntax highlighting, semantic tokens, diagnostics, go-to-definition, rename, and more.

[Full IDE setup guide](getting-started/vs-code.md)
