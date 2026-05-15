from typing import Any
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


def MyComponent(children: list[str], attributes: dict[str, Any]) -> str:
    return <>
        <div>Hello</div>
    </>


@router.get("/component", response_class=HTMLResponse)
async def component() -> str:
    style = {"color": "red"}
    return <>
        <div for={{ i in range(10) }} style={{ style }}>
            <MyComponent if={{ i % 2 == 0 }} />
        </div>
    </>
