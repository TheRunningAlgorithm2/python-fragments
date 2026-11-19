# Scripts and Styles

The bodies of `<script>` and `<style>` elements are raw text. They are passed through to the rendered HTML exactly as written, including all whitespace and indentation:

```python
def page() -> str:
    return <>
        <style>
            .card > h2 { margin: 0; }
        </style>
        <script>
            if (count < limit) {
                console.log("under the limit");
            }
        </script>
    </>
```

No fragment syntax is recognised inside the body. `<`, `{{ }}`, `<!-- -->` and `</>` are all plain text there, so JavaScript and CSS can be written without any escaping.

## Closing tags

The body ends at the first matching closing tag. It is matched case-sensitively, and whitespace is allowed before the `>`:

```python
<script>console.log("hello")</script >
```

`</SCRIPT>` and `</script/>` do not end the body. As in a browser, a `</script>` inside a JavaScript string does end it, so write `<\/script>` instead.

## Attributes

Attributes work exactly as they do on any other element, including expression attributes and [control flow](control-flow.md):

```python
<script src={{ static_url("app.js") }} nonce={{ csp_nonce }} defer></script>
<style if={{ dark_mode }}>
    body { background: black; }
</style>
```

## Self-closing tags

A self-closing `<script />` is transpiled as written. Browsers do not treat `<script />` as closed: they treat it as an opening tag, and everything after it becomes part of the script. Always write an explicit closing tag:

```python
<script src="app.js"></script>
```
