from typing import Any
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from dataclasses import dataclass
from datetime import datetime

router = APIRouter()


@dataclass
class Post:
    title: str
    date: datetime

POSTS: list[Post] = [
    Post("Python Fragments", datetime(2026, 5, 17)),
    Post("The Running Algorithm", datetime(2026, 5, 12)),
]

def PostCard(children: list[str], post: Post) -> str:
    return <>
        <div>
            <!-- Hello -->
            <h2>{{ post.title }}</h2>
            <p>{{ post.date.strftime("%d-%m-%y") }}</p>
        </div>
    </>


async def page() -> str:
    return <>
        <Base title="Test" header="Test Header">
            <PostCard for={{ post in POSTS }} post={{ post }} />
        </Base>
    </>
