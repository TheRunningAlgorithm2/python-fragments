from typing import Any
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from layouts import Base

router = APIRouter()

views: int = 0


@router.get("/", response_class=HTMLResponse)
async def page() -> str:
    global views
    views += 1
    return <>
        <Base title="Test" header="Test Header">
            <p>View Count:</p>
            <p>{{ views }}</p>
        </Base>
    </>
