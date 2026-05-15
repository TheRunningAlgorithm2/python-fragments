# Classes Attribute

As `class` is a reserved keyword in Python, we use the (arguably more accurate anyway) `classes` attribute. In the same fashion as [style](style-attribute.md) you may supply classes as either a string, or a list of strings.

```python
def my_component(...):
    works_fine = [...]
    return <>
        <div classes="works-fine"></div>
        <div classes={{ "works-fine" }}></div>
        <div classes={{ ["works-fine"] }}></div>
        <div classes={{ works_fine }}></div>
    </>
```