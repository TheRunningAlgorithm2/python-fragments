# Python Fragments

**Modern HTML template rendering in Python** - no build step, no template files, and native HTML awareness out of the box.

```python
def profile_page(user):
    style = {"color": "red" if user.is_admin else "blue"}
    return <>
        <h1 style={{ style }}>Hello, {{ user.username }}!</h1>
        <ul>
            <li for={{ post in user.recent_posts }}>
                {{ post.title }}
            </li>
        </ul>
    </>
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
    <p>Type checking, hover, completions, and semantic highlighting via a built-in language server and VS Code extension.</p>
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

[Full installation guide](installation.md)

### 2. Use With Your IDE

Install the language server for inline type errors, completions, and hover docs:

```bash
pip install python-fragments[lsp]
```

A **VS Code extension** is included with structural syntax highlighting, semantic tokens, diagnostics, and more.

[Full IDE setup guide](ide-tooling.md)
