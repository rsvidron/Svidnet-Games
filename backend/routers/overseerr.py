"""
Overseerr proxy router
Keeps the API key server-side; frontend never sees it.
"""
import os
import httpx
import logging
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/overseerr", tags=["overseerr"])

OVERSEERR_URL = "https://requests.svidnet.com"
OVERSEERR_API_KEY = os.getenv("OVERSEERR_API_KEY", "")


def _headers():
    return {
        "X-Api-Key": OVERSEERR_API_KEY,
        "Content-Type": "application/json",
    }


def _require_key():
    if not OVERSEERR_API_KEY:
        raise HTTPException(503, "Overseerr API key not configured")


def _require_auth(authorization: Optional[str]):
    if not authorization:
        raise HTTPException(401, "Authentication required")


@router.get("/status")
async def get_media_status(
    tmdb_id: int,
    media_type: str,  # "movie" or "tv"
    authorization: Optional[str] = Header(None),
):
    """
    Check Overseerr for the status of a movie or TV show.
    Returns one of: 'available', 'requested', 'not_requested'
    """
    _require_key()
    _require_auth(authorization)

    if media_type not in ("movie", "tv"):
        raise HTTPException(400, "media_type must be 'movie' or 'tv'")

    endpoint = "movie" if media_type == "movie" else "tv"

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            res = await client.get(
                f"{OVERSEERR_URL}/api/v1/{endpoint}/{tmdb_id}",
                headers=_headers(),
            )

        if res.status_code == 404:
            # Overseerr doesn't know about it yet — not requested
            return {"status": "not_requested", "tmdb_id": tmdb_id}

        if res.status_code != 200:
            logger.warning(f"Overseerr returned {res.status_code} for {media_type}/{tmdb_id}")
            return {"status": "unknown", "tmdb_id": tmdb_id}

        data = res.json()
        media_info = data.get("mediaInfo")

        if not media_info:
            return {"status": "not_requested", "tmdb_id": tmdb_id}

        # Overseerr status codes:
        # 1 = UNKNOWN, 2 = PENDING, 3 = PROCESSING, 4 = PARTIALLY_AVAILABLE, 5 = AVAILABLE
        overseerr_status = media_info.get("status", 1)

        if overseerr_status == 5:
            return {"status": "available", "tmdb_id": tmdb_id}
        elif overseerr_status == 4:
            return {"status": "available", "tmdb_id": tmdb_id}
        elif overseerr_status in (2, 3):
            return {"status": "requested", "tmdb_id": tmdb_id}
        else:
            return {"status": "not_requested", "tmdb_id": tmdb_id}

    except httpx.RequestError as e:
        logger.error(f"Overseerr connection error: {e}")
        raise HTTPException(502, "Could not reach Overseerr")


class RequestBody(BaseModel):
    tmdb_id: int
    media_type: str  # "movie" or "tv"


@router.post("/request")
async def request_media(
    body: RequestBody,
    authorization: Optional[str] = Header(None),
):
    """Submit a media request to Overseerr."""
    _require_key()
    _require_auth(authorization)

    if body.media_type not in ("movie", "tv"):
        raise HTTPException(400, "media_type must be 'movie' or 'tv'")

    payload = {
        "mediaType": body.media_type,
        "mediaId": body.tmdb_id,
    }
    # For TV, request all seasons by default
    if body.media_type == "tv":
        payload["seasons"] = "all"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(
                f"{OVERSEERR_URL}/api/v1/request",
                headers=_headers(),
                json=payload,
            )

        if res.status_code in (200, 201):
            return {"success": True, "status": "requested"}

        # 409 = already requested
        if res.status_code == 409:
            return {"success": True, "status": "already_requested"}

        logger.error(f"Overseerr request failed {res.status_code}: {res.text[:200]}")
        raise HTTPException(500, f"Overseerr error: {res.status_code}")

    except httpx.RequestError as e:
        logger.error(f"Overseerr connection error: {e}")
        raise HTTPException(502, "Could not reach Overseerr")
