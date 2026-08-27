from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.esp32 import (
    esp32_service,
)


# =============================================================
# ROUTER
# =============================================================

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

        status = (
            esp32_service.get_status()
        )

        return {
            "success": True,
            "data": status,
        }

    except Exception as exc:

        raise HTTPException(
            status_code=503,
            detail={
                "success": False,
                "error": str(exc),
            }
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

        result = (
            esp32_service.set_tracker(
                request.state
            )
        )

        return {
            "success": True,
            "device": "tracker",
            "requested_state": request.state,
            "result": result,
        }

    except Exception as exc:

        raise HTTPException(
            status_code=503,
            detail={
                "success": False,
                "device": "tracker",
                "error": str(exc),
            }
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

        result = (
            esp32_service.set_hm30(
                request.state
            )
        )

        return {
            "success": True,
            "device": "hm30",
            "requested_state": request.state,
            "result": result,
        }

    except Exception as exc:

        raise HTTPException(
            status_code=503,
            detail={
                "success": False,
                "device": "hm30",
                "error": str(exc),
            }
        ) from exc
    # =============================================================
# SSR1
# =============================================================

@router.post(
    "/control/ssr1"
)
def control_ssr1(
    request: ControlRequest
) -> dict[str, Any]:

    try:
        return esp32_service.set_ssr1(
            request.state
        )

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc)
        ) from exc


# =============================================================
# SSR2
# =============================================================

@router.post(
    "/control/ssr2"
)
def control_ssr2(
    request: ControlRequest
) -> dict[str, Any]:

    try:
        return esp32_service.set_ssr2(
            request.state
        )

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc)
        ) from exc


# =============================================================
# RELAY
# =============================================================

@router.post(
    "/control/relay"
)
def control_relay(
    request: ControlRequest
) -> dict[str, Any]:

    try:
        return esp32_service.set_relay(
            request.state
        )

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc)
        ) from exc