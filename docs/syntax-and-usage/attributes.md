# Attributes

## String attributes (default)

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

When using an interpolated value, fragments does not treat Python booleans specially — `True` and `False` are rendered as the strings `"true"` and `"false"` respectively:

```python
<input type="checkbox" checked={{ is_checked }} />
# is_checked=True  → <input type="checkbox" checked="true" />
# is_checked=False → <input type="checkbox" checked="false" />
```

To omit an attribute entirely, pass `None`:

```python
<input type="checkbox" checked={{ is_checked or None }} />
# is_checked=True  → <input type="checkbox" checked="true" />
# is_checked=False → <input type="checkbox" />
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
