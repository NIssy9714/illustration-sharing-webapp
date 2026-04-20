from fastapi import FastAPI

from fastapi_app.app.core.config import get_settings
from fastapi_app.app.routers import auth
from fastapi_app.app.routers import posts


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0")

    @app.get("/healthz")
    def healthz():
        return {"status": "ok", "env": settings.app_env}

    app.include_router(auth.router)
    app.include_router(posts.router)

    return app


app = create_app()

