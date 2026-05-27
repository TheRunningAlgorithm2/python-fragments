# Components

Any Python function can be used as a component. Components are distinguished from HTML elements by their name: **an uppercase first letter means a component call**, lowercase means a standard HTML element.

## Defining a component

A component is a plain Python function that returns a fragment. Attributes passed on the tag become keyword arguments — declare them explicitly or accept them all with `**kwargs`:

```python
def Card(children: list[str], classes: str = "") -> str:
    return <>
        <div classes={{ classes }}>
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

Attributes on the tag are forwarded as keyword arguments to the function:

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