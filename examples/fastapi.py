from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from fragments.html import elements

app = FastAPI()


@app.get("/component")
async def component():
    return HTMLResponse(
        elements.sequence(
            [
                elements.el(
                    "div",
                    [elements.el("p", ["Hello"], style={"color": "red"})],
                    classes=["test"],
                    style={"background-color": "green"},
                    attributes={"x-data": "{ test: 'test' }"},
                ),
            ]
        )
    )
