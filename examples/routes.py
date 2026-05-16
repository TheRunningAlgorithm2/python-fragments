from typing import Any
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from layouts import Base

router = APIRouter()

view_count: int = 0


@router.get("/", response_class=HTMLResponse)
async def page() -> str:
    global view_count
    view_count += 1
    return <>
        <Base title="Test" header="Test Header">
            <p>View Count:</p>
            <p>{{ view_count }}</p>
        </Base>
    </>
