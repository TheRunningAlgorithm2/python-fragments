# Control Flow

## Conditional rendering

Add an `if` attribute to any element to render it conditionally:

```python
return <>
    <p if={{ user.is_admin }}>Admin panel</p>
    <p if={{ not user.is_verified }}>Please verify your email.</p>
</>
```

The element is omitted entirely from the output when the condition is false.

## Loops

Add a `for` attribute to repeat an element over any iterable:

```python
return <>
    <ul>
        <li for={{ item in cart.items }}>
            {{ item.name }} — {{ item.price }}
        </li>
    </ul>
</>
```

`if` and `for` can be combined on the same element:

```python
<li for={{ post in posts }} if={{ post.published }}>
    {{ post.title }}
</li>
```
