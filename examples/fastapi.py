from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.responses import HTMLResponse


@dataclass
class Exercise:
    id: int
    name: str


LIST = [
    Exercise(0, "Bicep Curl"),
    Exercise(1, "Bench Press"),
    Exercise(2, "Lat Pulldown"),
]

app = FastAPI()


@app.get("/exercises/list", response_class=HTMLResponse)
def ExerciseList():
    exercise_names = [exercise.name for exercise in LIST]
    return "test"
