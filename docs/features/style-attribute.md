# Style Attribute Handling

The CSS `style` attribute can be read out of any dict, allowing for easy programmatic handling.

```python
def my_component(...):
    styles = {"color": "red"}
    return <>
        <h1 style={{ styles }}>Hello</h1>
    </>
```
