from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from fragments.html.elements import el, sequence

app = FastAPI()


@app.get("/component", response_class=HTMLResponse)
async def component():
    classes = ["test"]
    style = {"background-color": "green"}
    return sequence(
        [
            sequence(
                [
                    el(
                        "div",
                        [el("p", ["Hello"], {"style": {"color": "red"}}, False), el("p", ["Test"], {}, False) if i % 2 == 0 else ""],
                        {"classes": classes, "style": style, "x-data": "{ test: 'test' }"},
                        False,
                    )
                    for i in range(10)
                ]
            )
        ]
    )
