from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import run_schema_migrations
from app.health import collect_runtime_health
from app.logging_config import configure_secret_redaction_logging
from app.routes import router

configure_secret_redaction_logging()

@asynccontextmanager
async def lifespan(_: FastAPI):
    await run_schema_migrations()
    yield


app = FastAPI(title="ThriftLens API", lifespan=lifespan)
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/api/health")
async def health() -> dict:
    return await collect_runtime_health("thriftlens-api")
