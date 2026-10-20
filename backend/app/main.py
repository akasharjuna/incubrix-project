"""FastAPI application factory."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, jobs
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.storage.job_store import initialize_store


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.debug)
    settings.ensure_dirs()
    initialize_store()

    app = FastAPI(
        title="B-roll Video Engine",
        description="Script and Voiceover to B-roll Video Engine — IncuBrix Assessment",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(jobs.router)

    return app


app = create_app()
