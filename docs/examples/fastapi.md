# FastAPI Example

A small blog application showing how Fragments fits into a real FastAPI project. It covers layout components, component composition, conditional rendering, and list rendering across two routes.

## Project structure

```
app/
├── main.py        # FastAPI app and loader registration
├── models.py      # Data model
├── components.py  # Reusable components
└── routes.py      # Route handlers
```

## models.py

A plain dataclass to represent a blog post:

```python
from dataclasses import dataclass, field

@dataclass
class Post:
    slug: str
    title: str
    summary: str
    body: str
    author: str
    published: bool = True
```

## components.py

Two components: a full-page layout wrapper, and a post card used in the listing.

```python
from typing import Any
from models import Post

def Layout(children: list[str], attributes: dict[str, Any]) -> str:
    title = attributes.get("title", "My Blog")
    return <>
        <html lang="en">
            <head>
                <meta charset="utf-8" />
                <title>{{ title }}</title>
                <meta name="viewport" content="width=device-width, initial-scale=1" />
                <link rel="stylesheet" href="/static/styles.css" />
            </head>
            <body>
                <header>
                    <a href="/" classes="site-title">My Blog</a>
                </header>
                <main>
                    {{ children }}
                </main>
            </body>
        </html>
    </>


def PostCard(children: list[str], attributes: dict[str, Any]) -> str:
    post: Post = attributes["post"]
    return <>
        <article classes="post-card">
            <h2>
                <a href={{ f"/posts/{post.slug}" }}>{{ post.title }}</a>
            </h2>
            <p classes="summary">{{ post.summary }}</p>
            <p classes="byline">By {{ post.author }}</p>
        </article>
    </>
```

`Layout` receives `title` from its attributes and `children` from whatever is nested inside `<Layout>...</Layout>`. `PostCard` pulls the `Post` object from its attributes — it ignores `children` since it's always self-closing.

## routes.py

Two routes: a post listing and a detail view.

```python
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from models import Post
from components import Layout, PostCard

router = APIRouter()

POSTS = [
    Post(
        slug="getting-started",
        title="Getting Started with Fragments",
        summary="How to add Python Fragments to an existing FastAPI app.",
        body="<p>Python Fragments lets you write HTML directly in .py files...</p>",
        author="Alice",
    ),
    Post(
        slug="component-patterns",
        title="Component Patterns",
        summary="Layout wrappers, cards, and other patterns that keep views clean.",
        body="<p>The key insight is that a component is just a function...</p>",
        author="Bob",
    ),
    Post(
        slug="upcoming-features",
        title="Upcoming Features",
        summary="What's coming next.",
        body="",
        author="Alice",
        published=False,
    ),
]

_by_slug: dict[str, Post] = {p.slug: p for p in POSTS}


@router.get("/", response_class=HTMLResponse)
async def index() -> str:
    published = [p for p in POSTS if p.published]
    return <>
        <Layout title="My Blog">
            <h1>Latest Posts</h1>
            <PostCard for={{ post in published }} post={{ post }} />
        </Layout>
    </>


@router.get("/posts/{slug}", response_class=HTMLResponse)
async def post_detail(slug: str) -> str:
    post = _by_slug.get(slug)
    if post is None or not post.published:
        raise HTTPException(status_code=404)
    return <>
        <Layout title={{ post.title }}>
            <article>
                <h1>{{ post.title }}</h1>
                <p classes="byline"><em>By {{ post.author }}</em></p>
                {{ post.body }}
            </article>
            <a href="/" classes="back-link">← All posts</a>
        </Layout>
    </>
```

The `for` attribute on `<PostCard>` renders one card per post, passing each post object through as an attribute. Unpublished posts are filtered in Python before the fragment runs — keeping the markup free of business logic.

## main.py

Register the loader before any fragment-containing modules are imported:

```python
from fragments import loader  # isort: skip

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from routes import router

app = FastAPI()
app.include_router(router)
```

The `# isort: skip` comment prevents import sorters from moving the loader import below `routes`, which would cause fragment syntax to be parsed before the transpiler is active.
