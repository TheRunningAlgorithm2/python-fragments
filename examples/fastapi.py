from fragments import frag_loader

frag_loader.init()

from fastapi import FastAPI

from examples.routes import router

app = FastAPI()

app.include_router(router)
