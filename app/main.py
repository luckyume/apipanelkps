from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.status import (
    router as status_router,
)


# =============================================================
# LIFESPAN
# =============================================================

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


# =============================================================
# FASTAPI
# =============================================================

app = FastAPI(

    title="Panel Kopasus API",

    description=(
        "API untuk membaca status dan "
        "mengontrol ESP32 melalui USB Serial."
    ),

    version="2.0.0",

    lifespan=lifespan,
)


# =============================================================
# ROUTER
# =============================================================

app.include_router(
    status_router
)


# =============================================================
# ROOT
# =============================================================

@app.get("/")
def root():

    return {

        "name": "Panel Kopasus API",

        "status": "running",

        "source": "ESP32 USB Serial",

    }