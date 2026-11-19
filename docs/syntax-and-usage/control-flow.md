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

When combined, `if` filters each item, reading like `for post in posts if post.published`. It is evaluated once per item and can refer to the loop variable. The order of the two attributes does not matter.

## Template

Use `<Template>` to apply `if` or `for` to a group of elements without wrapping them in an extra element. `<Template>` renders only its children:

```python
return <>
    <dl>
        <Template for={{ term in glossary }}>
            <dt>{{ term.name }}</dt>
            <dd>{{ term.definition }}</dd>
        </Template>
    </dl>
</>
```

`if` and `for` work on `<Template>` exactly as they do on elements, including when combined:

```python
<Template for={{ post in posts }} if={{ post.published }}>
    <h2>{{ post.title }}</h2>
    <p>{{ post.summary }}</p>
</Template>
```

To check a condition once for a whole loop, rather than once per item, nest two templates:

```python
<Template if={{ user.is_admin }}>
    <Template for={{ report in reports }}>
        <ReportRow report={{ report }} />
    </Template>
</Template>
```

`<Template>` only accepts `if` and `for` attributes, and both must be interpolations. It cannot be self-closing. A `<Template>` with no attributes is allowed and simply renders its children.

## Components

`if` and `for` work on component tags too:

```python
<PostCard for={{ post in published }} post={{ post }} />
<Banner if={{ show_banner }} />
```

They are purely structural — the transpiler handles them before the call is emitted, so neither `if` nor `for` is ever passed as a keyword argument to the component function.
