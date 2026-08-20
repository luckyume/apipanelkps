from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.esp32 import (
    esp32_service,
)


router = APIRouter(
    tags=["ESP32"]
)


# =============================================================
# REQUEST MODEL
# =============================================================

class ControlRequest(BaseModel):
    state: bool


# =============================================================
# GET STATUS
# =============================================================

@router.get(
    "/status"
)
def get_status() -> dict[str, Any]:

    try:

        return esp32_service.get_status()

    except Exception as exc:

        raise HTTPException(
            status_code=503,
            detail=str(exc)
        ) from exc


# =============================================================
# TRACKER
# =============================================================

@router.post(
    "/control/tracker"
)
def control_tracker(
    request: ControlRequest
) -> dict[str, Any]:

    try:

        return esp32_service.set_tracker(
            request.state
        )

    except Exception as exc:

        raise HTTPException(
            status_code=503,
            detail=str(exc)
        ) from exc


# =============================================================
# HM30
# =============================================================

@router.post(
    "/control/hm30"
)
def control_hm30(
    request: ControlRequest
) -> dict[str, Any]:

    try:

        return esp32_service.set_hm30(
            request.state
        )

    except Exception as exc:

        raise HTTPException(
            status_code=503,
            detail=str(exc)
        ) from exc