from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/component", response_class=HTMLResponse)
async def component():
    return <>
        <div for={{ i in range(10) }}>
            {{ i }}
        </div>
    </>
