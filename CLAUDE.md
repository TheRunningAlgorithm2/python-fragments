# Overview

This project is a transpiler designed to bring HTML into Python, similar to how Babel and JSX brings HTML into JavaScript.

It allows a jinja-like syntax to be used inline in Python, like this:

```python
@app.route("/")
def index_page(user: Annotated[User, RoutedUser()]):
    return <>
        <h1>Hello, {{ user.username }}!</h1>
    </>
```

Which is transpiled into working Python like this:

```python
@app.route("/")
def index_page(user: Annotated[User, RoutedUser()]):
    return sequence([el("div", ...)])
```

The benefits of which are:

1. Faster than Jinja (no file I/O)
2. Native HTML awareness (more compressed HTML payloads)
3. Substantially better developer experience (it's all just in Python)
4. No build step

# Project Structure

This repo contains:

* The transpiler library code (in @fragments/ )
* Example implementations in @examples/

# Installing and Importing

We use a custom importlib loader, defined in @fragments/loader.py , to transpile ".py" files that contian fragments at the point that they are imported, so it works seamlessly with existing Python code bases and does not require a build step, like Go's Templ.
