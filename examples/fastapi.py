from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()


@app.get("/component", response_class=HTMLResponse)
async def component():
    classes = ["test"]
    style = {"background-color": "green"}
    return <>
        <div for={{ i in range(10) }} classes={{ classes }} style={{ style }} x-data="{ test: 'test' }">
            <p style={{ {"color": "red"} }}>Hello</p>
            <p if={{ i % 2 == 0 }}> Test</p>
        </div>
    </>
