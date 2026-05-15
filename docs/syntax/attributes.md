# Attributes

## String attributes

Plain string values work exactly as in HTML:

```python
<button type="submit">Save</button>
```

## Expression attributes

Use `{{ }}` to pass any Python expression as an attribute value:

```python
<a href={{ page.url }} id={{ page.slug }}>{{ page.title }}</a>
```

## Boolean attributes

Attributes with no value are passed through as-is:

```python
<input type="checkbox" checked />
```

## Style

The `style` attribute accepts a dict. Keys are CSS property names, values are strings:

```python
styles = {"color": "red", "font-weight": "bold"}

return <>
    <p style={{ styles }}>Important</p>
</>
```

## Classes

As `class` is a reserved keyword in Python, use `classes` instead. It accepts a plain string or a list of strings:

```python
<div classes="card"></div>
<div classes={{ "card" }}></div>
<div classes={{ ["card", "highlighted"] }}></div>
<div classes={{ active_classes }}></div>
```
