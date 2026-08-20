from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.status import (
    router as status_router
)


@asynccontextmanager
async def lifespan(
    app: FastAPI
):

    print(
        "========================================"
    )

    print(
        "PANEL KOPASUS API STARTING"
    )

    print(
        "========================================"
    )

    yield

    print(
        "PANEL KOPASUS API STOPPING"
    )


app = FastAPI(
    title="Panel Kopasus API",
    description=(
        "API untuk membaca status dan "
        "mengontrol ESP32 melalui USB Serial."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


app.include_router(
    status_router
)


@app.get("/")
def root():

    return {
        "name": "Panel Kopasus API",
        "status": "running",
        "source": "ESP32 USB Serial",
    }