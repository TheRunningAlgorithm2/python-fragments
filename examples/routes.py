from typing import Any
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from layouts import Base
from dataclasses import dataclass
from datetime import datetime
from fragments.types import Children

router = APIRouter()

view_counter: int = 0


@dataclass
class Post:
    title: str
    date: datetime

POSTS: list[Post] = [
    Post("Python Fragments", datetime(2026, 5, 17)),
    Post("The Running Algorithm", datetime(2026, 5, 12)),
]

def PostCard(children: Children, post: Post) -> str:
    return <>
        <div>
            <h2>{{ post.title }}</h2>
            <p>{{ post.date.strftime("%d-%m-%y") }}</p>
        </div>
    </>


@router.get("/", response_class=HTMLResponse)
async def page() -> str:
    global view_counter
    view_counter += 1
    return <>
        <Base title="Test" header="Test Header">
            <p if={{ True }}>Hello</p>
            <p x-data="{ test: 'a' }">Views: {{ view_counter }}</p>
            <PostCard for={{ post in POSTS }} post={{ post }} />
        </Base>
    </>
