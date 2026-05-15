# Fragments

A fragment is a block of HTML written inline in Python, delimited by `<>` and `</>`.

```python
def my_view():
    return <>
        <h1>Hello</h1>
        <p>Welcome.</p>
    </>
```

Fragments can appear anywhere a Python expression can — as a return value, in an assignment, or passed as an argument.

## Interpolation

Embed any Python expression inside `{{ }}`:

```python
def greeting(name: str):
    return <>
        <h1>Hello, {{ name }}!</h1>
        <p>You have {{ len(messages) }} messages.</p>
    </>
```

Interpolations can also appear in attribute values:

```python
<a href={{ user.profile_url }}>Profile</a>
```

## Elements

Standard HTML elements work as expected. Use self-closing syntax for void elements:

```python
return <>
    <section>
        <img src={{ avatar_url }} />
        <p>{{ bio }}</p>
        <hr />
    </section>
</>
```
