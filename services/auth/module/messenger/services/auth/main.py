from fastapi import FastAPI

from messenger.shared.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=settings.app_name)

    @application.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "environment": settings.environment,
        }

    return application


app = create_app()
