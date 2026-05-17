# Interpolation

Embed any Python expression inside `{{ }}`:

```python
def greeting(name: str):
    return <>
        <h1>Hello, {{ name }}!</h1>
        <p>You have {{ len(messages) }} messages.</p>
    </>
```

The same syntax works in attribute values — see [Attributes](attributes.md) for details.
