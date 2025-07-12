from dataclasses import dataclass


@dataclass
class Exercise:
    id: int
    name: str


LIST = [
    Exercise(0, "Bicep Curl"),
    Exercise(1, "Bench Press"),
    Exercise(2, "Lat Pulldown"),
]
