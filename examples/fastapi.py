from fragments import frag_loader

frag_loader.init()

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from examples import exercise
from examples.exercise_list import ExerciseList

app = FastAPI()


@app.get("/exercise/list")
async def exercise_lister():
    return HTMLResponse(ExerciseList(exercise.LIST))
