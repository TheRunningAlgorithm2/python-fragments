# Comments

HTML comments use the standard `<!-- -->` syntax and can appear anywhere inside a fragment:

```python
def my_view() -> str:
    return <>
        <!-- page header -->
        <h1>Hello</h1>
        <p>Welcome.</p>
    </>
```

Comments are passed through to the rendered HTML output unchanged:

```html
<!-- page header --><h1>Hello</h1><p>Welcome.</p>
```

## Inside elements

Comments can appear as children of any HTML element:

```python
<ul>
    <!-- items are filtered before rendering -->
    <li for={{ item in published_items }}>{{ item.name }}</li>
</ul>
```

## Multiline comments

Comments may span multiple lines:

```python
<>
    <!--
        TODO: replace with a dynamic component once the API is ready
    -->
    <div classes="placeholder">Coming soon</div>
</>
```
