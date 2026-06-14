<p align="center">
  <img src="logo.svg" alt="Python Fragments" width="300" />
</p>

<p align="center">
  <a href="https://github.com/TheRunningAlgorithm2/python-fragments/actions/workflows/test.yml"><img src="https://github.com/TheRunningAlgorithm2/python-fragments/actions/workflows/test.yml/badge.svg" alt="Tests" /></a>
  <a href="https://pypi.org/project/python-fragments/"><img src="https://img.shields.io/pypi/v/python-fragments" alt="PyPI version" /></a>
  <a href="https://pypi.org/project/python-fragments/"><img src="https://img.shields.io/pypi/pyversions/python-fragments" alt="Python versions" /></a>
  <a href="https://github.com/TheRunningAlgorithm2/python-fragments/blob/main/LICENSE"><img src="https://img.shields.io/github/license/TheRunningAlgorithm2/python-fragments" alt="License" /></a>
  <a href="https://python-fragments.io"><img src="https://img.shields.io/badge/docs-python--fragments.io-blue" alt="Documentation" /></a>
  <a href="https://marketplace.visualstudio.com/items?itemName=tra-technologies-ltd.python-fragments"><img src="https://img.shields.io/badge/VS%20Code-Extension-blue?logo=visualstudiocode" alt="VS Code Extension" /></a>
</p>

> **This package is in early development and not yet stable. The API may change without notice between releases.**

Modern HTML template rendering in Python. No build step, no template files, and native HTML awareness out of the box.

```python
from fastapi import APIRouter

router = APIRouter()

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

## IDE Support

Type checking, completions, hover docs, go-to-definition, rename, and semantic highlighting. All working inside fragment syntax.

Install the [Python Fragments VS Code extension](https://marketplace.visualstudio.com/items?itemName=tra-technologies-ltd.python-fragments) to get started.

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

## Documentation

Full documentation is available at [python-fragments.io](https://python-fragments.io).

## Contributing

Bug reports, feature requests, and documentation improvements are all welcome. Code contributions aren't open yet while we work toward v1. See [CONTRIBUTING.md](CONTRIBUTING.md) for details.
