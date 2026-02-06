import logging
import traceback

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config import Config

format = "%(levelname)s:%(funcName)s:%(message)s"
logging.basicConfig(level=Config.LOG_LEVEL, format=format)


def create_app():
    app = FastAPI(
        title=Config.PROJECT_NAME,
        description=Config.PROJECT_DESCRIPTION,
        contact={"email": Config.CONTACT_EMAIL},
        termsOfService=Config.TERMS_OF_SERVICE,
        host=Config.SERVER_HOST,
    )

    async def catch_exceptions_middleware(request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            logging.error(traceback.format_exc())
            if isinstance(exc, HTTPException):
                raise exc
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": str(exc),
                    "message": "Something went wrong!",
                },
            )

    app.middleware("http")(catch_exceptions_middleware)

    # add CORS
    if Config.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in Config.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Include API handler router
    from src.api_handler import api_router
    from src.user.models import Invoice, Stock, Payment, QRCode
    from utils.db.base import ModelBase
    from utils.db.session import engine

    @app.on_event("startup")
    def _ensure_tables():
        """Create stock, invoice, payment, and qr_code tables if they do not exist (e.g. when Alembic revision is out of sync)."""
        try:
            ModelBase.metadata.create_all(
                engine,
                tables=[Stock.__table__, Invoice.__table__, Payment.__table__, QRCode.__table__],
                checkfirst=True,
            )
        except Exception as e:
            logging.warning("Could not ensure tables exist: %s", e)

    # include main router
    app.include_router(api_router)

    # controller routes
    @app.get("/", tags=["API Base"])
    def _get():
        return f"Welcome to {Config.PROJECT_NAME} APIs. Up and running!"

    return app
