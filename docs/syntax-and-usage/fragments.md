# Fragments

A fragment is a block of HTML written inline in Python, delimited by `<>` and `</>`. At runtime, a fragment is transpiled into a function call that returns a plain Python string — so you can use one anywhere you would use a string.

```python
def my_view():
    return <>
        <h1>Hello</h1>
        <p>Welcome.</p>
    </>
```

Because a fragment evaluates to a string, it can appear as a return value, in an assignment, passed as an argument, or in any other string context:

`<>` and `</>` inside Python string literals or line comments are not treated as fragment delimiters, so code like `assert result == "<p>hello</p>"` or `# renders a <> fragment </>` is safe.

```python
# As a return value
def my_view() -> str:
    return <>
        <h1>Hello</h1>
    </>

# In an assignment
html = <><p>Some content</p></>

# Passed as an argument
response = HTMLResponse(<><h1>Hello</h1></>)
```
