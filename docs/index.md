# Python Fragments

Modern HTML template rendering in Python - no build step, and no template files.

<b>
    <ul>
        <li>No build step</li>
        <li>Lightning fast interpolation</li>
        <li>Native HTML awareness</li>
    <ul>
</b>

```python
def profile_page(...):
    style = {"color": "red" if user.is_admin else "blue"}
    return <>
        <h1 style={{ style }}>Hello, {{ user.username }}!</h1>
        <ul>
            <li for={{ post in user.recent_posts }}>
                {{ post.title }}
            </li>
        </ul>
    </>
```
