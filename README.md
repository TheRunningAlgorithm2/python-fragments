<p align="center">
  <img src="logo.svg" alt="Python Fragments" width="300" />
</p>

<p align="center">
  <a href="https://github.com/TheRunningAlgorithm2/python-fragments/actions/workflows/test.yml"><img src="https://github.com/TheRunningAlgorithm2/python-fragments/actions/workflows/test.yml/badge.svg" alt="Tests" /></a>
  <a href="https://pypi.org/project/python-fragments/"><img src="https://img.shields.io/pypi/v/python-fragments" alt="PyPI version" /></a>
  <a href="https://pypi.org/project/python-fragments/"><img src="https://img.shields.io/pypi/pyversions/python-fragments" alt="Python versions" /></a>
  <a href="https://github.com/TheRunningAlgorithm2/python-fragments/blob/main/LICENSE"><img src="https://img.shields.io/github/license/TheRunningAlgorithm2/python-fragments" alt="License" /></a>
</p>

> **This package is in early development and not yet stable. The API may change without notice between releases.**

Modern HTML template rendering in Python — no build step, no template files, and native HTML awareness out of the box.

```python
from fragments import loader  # isort: skip

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from components import Layout, PostCard

app = FastAPI()

POSTS = [...]

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

## IDE Support

Type checking, completions, hover docs, go-to-definition, rename, and semantic highlighting — all working inside fragment syntax.

![VS Code completions demo](docs/assets/vscode.gif)

## Installation

```bash
pip install python-fragments
```

Register the loader at your application's entry point, before importing any modules that contain fragments:

```python
from fragments import loader  # isort: skip
```

Any `.py` file containing `<>` is transpiled automatically. Nothing else to configure.

## Feedback and feature requests

Bug reports and feature requests are welcome via [GitHub Issues](https://github.com/TheRunningAlgorithm2/python-fragments/issues). The project is not currently accepting code contributions.
