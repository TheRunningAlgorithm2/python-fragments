# Python Fragments

**Modern HTML template rendering in Python** - no build step, no template files, and native HTML awareness out of the box.

=== "Plain Python"

    ```python
    # main.py
    from fragments import loader

    from views import render_index
    ```

    ```python
    # views.py
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
    # main.py
    from fragments import loader

    from fastapi import FastAPI
    from .index import router

    app = FastAPI()
    app.include_router(router)
    ```

    ```python
    # index.py
    from fastapi import APIRouter
    from fastapi.responses import HTMLResponse

    router = APIRouter()

    POSTS = [...]  # your data here

    @router.get("/", response_class=HTMLResponse)
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
    # app.py
    from fragments import loader

    from flask import Flask
    from views import index_bp

    app = Flask(__name__)
    app.register_blueprint(index_bp)
    ```

    ```python
    # views.py
    from flask import Blueprint

    index_bp = Blueprint("index", __name__)

    POSTS = [...]  # your data here

    @index_bp.route("/")
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
    # urls.py
    from fragments import loader

    from django.urls import path
    from views import index

    urlpatterns = [path("", index)]
    ```

    ```python
    # views.py
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

<div class="grid cards" markdown>

-   ### No build step

    Transpiled automatically at import time. No CLI, no watchers, no separate compile phase.

-   ### Full IDE Support

    Type checking, hover, completions, go-to-definition, rename, and semantic highlighting via a built-in language server and VS Code extension.

-   ### Production Tested

    Used in production and developed in-house by [TheRunningAlgorithm](https://www.therunningalgorithm.com), exposed to thousands of live users prior to open source release

-   ### Long Term Support

    Actively maintained by [TheRunningAlgorithm](https://www.therunningalgorithm.com), who use it in production.

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

A **[VS Code extension](https://marketplace.visualstudio.com/items?itemName=tra-technologies-ltd.python-fragments)** is available on the Marketplace with structural syntax highlighting, semantic tokens, diagnostics, go-to-definition, rename, and more.

[Full IDE setup guide](getting-started/vs-code.md)
