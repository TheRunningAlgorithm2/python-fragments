from fragments import loader  # isort: skip
from fastapi import FastAPI

from examples.routes import router

app = FastAPI()

app.include_router(router)
