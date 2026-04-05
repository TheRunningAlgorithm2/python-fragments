from fragments import frag_loader

frag_loader.init()

import uvicorn
from examples.fastapi import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
