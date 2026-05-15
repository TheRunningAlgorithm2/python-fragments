# Components

Any Python function can be used as a component. Components are distinguished from HTML elements by their name: **an uppercase first letter means a component call**, lowercase means a standard HTML element.

## Defining a component

A component is a plain Python function that returns a fragment:

```python
def Card(children: list[str], attributes: dict) -> str:
    return <>
        <div classes="card">
            {{ children }}
        </div>
    </>
```

## Using a component

Use it like an HTML tag:

```python
return <>
    <Card>
        <p>Some content</p>
    </Card>
</>
```

Children are passed as the first argument, and any attributes are passed as the second:

```python
<Card classes="featured">
    <p>Highlighted content</p>
</Card>
```

## Self-closing components

Components with no children can use self-closing syntax:

```python
<Avatar src={{ user.avatar_url }} />
```
