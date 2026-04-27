from fastapi import FastAPI

from app.api.research import router

app = FastAPI(title="API Gateway", version="0.1.0")

app.include_router(router, prefix="/research", tags=["research"])


@app.get("/health")
async def health():
    return {"status": "ok"}
