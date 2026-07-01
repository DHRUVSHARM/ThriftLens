from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import run_schema_migrations
from app.health import collect_runtime_health
from app.routes import router


@asynccontextmanager
async def lifespan(_: FastAPI):
    await run_schema_migrations()
    yield


app = FastAPI(title="ThriftLens API", lifespan=lifespan)
app.include_router(router)


@app.get("/api/health")
async def health() -> dict:
    return await collect_runtime_health("thriftlens-api")
