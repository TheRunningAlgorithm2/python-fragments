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

## Scripts and styles

Interpolation is not supported inside `<script>` or `<style>` bodies, where `{{ }}` is plain text (see [Scripts and Styles](scripts-and-styles.md)). To pass data to a script, use an attribute instead. Dicts and lists are JSON-encoded and HTML-escaped:

```python
<div id="app" data-config={{ config }}></div>
<script>
    const config = JSON.parse(document.getElementById("app").dataset.config);
</script>
```
