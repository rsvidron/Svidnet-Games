"""
Movie & TV review endpoints — search via TMDB, track watchlists and reviews.
"""
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel
from jose import jwt, JWTError
import httpx
import os
import sys
import time

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from models.media_review import MediaReview

router = APIRouter(prefix="/api/reviews", tags=["reviews"])

# ── TMDB Configuration ──────────────────────────────────────────────────────
TMDB_BEARER = os.getenv(
    "TMDB_BEARER_TOKEN",
    "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiI2ZjRlMGZhZWJjZTY3Yjk4NzYxMmIxZmZjZmI3ODg1ZSIsIm5iZiI6MTcyMjQ0MzkzMi43OTcsInN1YiI6IjY2YWE2ODljNTliYWI3OGRiNzBhZjhiNSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.4Y4Lu7P-vaFpK07YlMutOHD5yuk4iATpWF28K4yapTQ"
)
TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_HEADERS = {
    "Authorization": f"Bearer {TMDB_BEARER}",
    "accept": "application/json",
}

# ── In-memory TTL cache for trending (10 min) ────────────────────────────────
_trending_cache: dict = {}   # key → {"data": ..., "ts": float}
TRENDING_TTL = 600           # seconds


# ── DB Session ───────────────────────────────────────────────────────────────
def get_db():
    from database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Auth helper ──────────────────────────────────────────────────────────────
def get_current_user_id(authorization: Optional[str] = Header(None)) -> int:
    """Decode JWT and return user_id as int. Raises 401 on any failure."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.removeprefix("Bearer ").strip()
    # Read at call time so Railway env var is always current
    secret = os.getenv("SECRET_KEY", "test-secret-key-for-development")
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        # sub is stored as int by create_token — use is None check (not falsy)
        user_id = payload.get("sub")
        if user_id is None:
            user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token claims")
        return int(user_id)
    except HTTPException:
        raise
    except JWTError as e:
        print(f"[reviews] JWT error: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    except Exception as e:
        print(f"[reviews] Auth error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ── Pydantic Schemas ─────────────────────────────────────────────────────────
class ReviewCreate(BaseModel):
    media_id: str
    media_type: str          # "movie" or "tv"
    title: str
    original_title: Optional[str] = None
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    overview: Optional[str] = None
    release_year: Optional[str] = None
    genres: Optional[str] = None
    status: str = "watchlist"   # watchlist / watched / dropped
    rating: Optional[int] = None
    review_text: Optional[str] = None


class ReviewUpdate(BaseModel):
    status: Optional[str] = None
    rating: Optional[int] = None
    review_text: Optional[str] = None


# ── Debug endpoint (remove after verifying auth works) ───────────────────────
@router.get("/debug-token")
def debug_token(authorization: Optional[str] = Header(None)):
    """Decode whatever token the browser sends and show its raw payload."""
    if not authorization:
        return {"error": "No Authorization header"}
    token = authorization.removeprefix("Bearer ").strip()
    secret = os.getenv("SECRET_KEY", "test-secret-key-for-development")
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return {"ok": True, "payload": payload, "secret_key_env_set": bool(os.getenv("SECRET_KEY"))}
    except JWTError as e:
        # Try decode without verification to see the raw claims
        try:
            import base64, json
            parts = token.split(".")
            padded = parts[1] + "=" * (4 - len(parts[1]) % 4)
            raw = json.loads(base64.urlsafe_b64decode(padded))
            return {"ok": False, "jose_error": str(e), "raw_claims": raw}
        except Exception as e2:
            return {"ok": False, "jose_error": str(e), "decode_error": str(e2)}


# ── TMDB Search ──────────────────────────────────────────────────────────────
@router.get("/search")
async def search_media(
    q: str = Query(..., min_length=1),
    media_type: str = Query("multi", regex="^(multi|movie|tv)$"),
    page: int = Query(1, ge=1, le=500),
):
    """Search TMDB for movies and/or TV shows."""
    if media_type == "multi":
        url = f"{TMDB_BASE}/search/multi"
    elif media_type == "movie":
        url = f"{TMDB_BASE}/search/movie"
    else:
        url = f"{TMDB_BASE}/search/tv"

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers=TMDB_HEADERS, params={"query": q, "page": page, "include_adult": False})

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="TMDB search failed")

    data = resp.json()
    results = []
    for item in data.get("results", []):
        mt = item.get("media_type", media_type)
        if mt not in ("movie", "tv"):
            continue
        results.append(_normalize_tmdb(item, mt))

    return {"results": results, "total_results": data.get("total_results", len(results)), "page": page, "total_pages": data.get("total_pages", 1)}


@router.get("/trending")
async def trending_media(
    media_type: str = Query("all", regex="^(all|movie|tv)$"),
    time_window: str = Query("week", regex="^(day|week)$"),
):
    """Fetch TMDB trending content with a 10-minute in-memory cache."""
    cache_key = f"{media_type}:{time_window}"
    cached = _trending_cache.get(cache_key)
    if cached and (time.time() - cached["ts"]) < TRENDING_TTL:
        return cached["data"]

    url = f"{TMDB_BASE}/trending/{media_type}/{time_window}"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers=TMDB_HEADERS)
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="TMDB request failed")
    data = resp.json()
    results = [
        _normalize_tmdb(item, item.get("media_type", "movie"))
        for item in data.get("results", [])
        if item.get("media_type") in ("movie", "tv")
    ]
    result = {"results": results, "cached": False}
    _trending_cache[cache_key] = {"data": {**result, "cached": False}, "ts": time.time()}
    return result


@router.get("/details/{media_type}/{media_id}")
async def get_media_details(media_type: str, media_id: str):
    """Fetch detailed info for a movie or TV show from TMDB."""
    if media_type not in ("movie", "tv"):
        raise HTTPException(status_code=400, detail="media_type must be 'movie' or 'tv'")
    url = f"{TMDB_BASE}/{media_type}/{media_id}"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers=TMDB_HEADERS, params={"append_to_response": "credits,videos"})
    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="Not found on TMDB")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="TMDB request failed")
    return resp.json()


# ── User Review CRUD ─────────────────────────────────────────────────────────
@router.get("/my")
def get_my_reviews(
    status: Optional[str] = Query(None),
    media_type: Optional[str] = Query(None),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Return the current user's reviews / watchlist."""
    q = db.query(MediaReview).filter(MediaReview.user_id == user_id)
    if status:
        q = q.filter(MediaReview.status == status)
    if media_type:
        q = q.filter(MediaReview.media_type == media_type)
    reviews = q.order_by(desc(MediaReview.updated_at)).all()
    return [_review_dict(r) for r in reviews]


@router.post("/my")
def create_review(
    body: ReviewCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Add a movie/TV show to the user's list (or update if already exists)."""
    existing = db.query(MediaReview).filter(
        MediaReview.user_id == user_id,
        MediaReview.media_id == body.media_id,
        MediaReview.media_type == body.media_type,
    ).first()

    if existing:
        existing.status = body.status
        if body.rating is not None:
            existing.rating = body.rating
        if body.review_text is not None:
            existing.review_text = body.review_text
        existing.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        return _review_dict(existing)

    review = MediaReview(
        user_id=user_id,
        media_id=body.media_id,
        media_type=body.media_type,
        title=body.title,
        original_title=body.original_title,
        poster_path=body.poster_path,
        backdrop_path=body.backdrop_path,
        overview=body.overview,
        release_year=body.release_year,
        genres=body.genres,
        status=body.status,
        rating=body.rating,
        review_text=body.review_text,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return _review_dict(review)


@router.patch("/my/{review_id}")
def update_review(
    review_id: int,
    body: ReviewUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Update status, rating, or review text."""
    review = db.query(MediaReview).filter(
        MediaReview.id == review_id,
        MediaReview.user_id == user_id,
    ).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    if body.status is not None:
        review.status = body.status
    if body.rating is not None:
        review.rating = body.rating
    if body.review_text is not None:
        review.review_text = body.review_text
    review.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(review)
    return _review_dict(review)


@router.delete("/my/{review_id}")
def delete_review(
    review_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Remove an entry from the user's list."""
    review = db.query(MediaReview).filter(
        MediaReview.id == review_id,
        MediaReview.user_id == user_id,
    ).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    db.delete(review)
    db.commit()
    return {"ok": True}


@router.get("/my/check/{media_type}/{media_id}")
def check_in_list(
    media_type: str,
    media_id: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Check if a specific title is already in the user's list."""
    review = db.query(MediaReview).filter(
        MediaReview.user_id == user_id,
        MediaReview.media_id == media_id,
        MediaReview.media_type == media_type,
    ).first()
    return {"in_list": review is not None, "review": _review_dict(review) if review else None}


# ── Helpers ──────────────────────────────────────────────────────────────────
def _normalize_tmdb(item: dict, media_type: str) -> dict:
    is_movie = media_type == "movie"
    title = item.get("title") if is_movie else item.get("name")
    original_title = item.get("original_title") if is_movie else item.get("original_name")
    date_str = item.get("release_date") if is_movie else item.get("first_air_date")
    year = date_str[:4] if date_str else None
    genres = ",".join(str(g) for g in item.get("genre_ids", []))
    return {
        "id": str(item.get("id")),
        "media_type": media_type,
        "title": title,
        "original_title": original_title,
        "poster_path": item.get("poster_path"),
        "backdrop_path": item.get("backdrop_path"),
        "overview": item.get("overview"),
        "release_year": year,
        "vote_average": item.get("vote_average"),
        "popularity": item.get("popularity"),
        "genres": genres,
    }


def _review_dict(r: MediaReview) -> dict:
    return {
        "id": r.id,
        "media_id": r.media_id,
        "media_type": r.media_type,
        "title": r.title,
        "original_title": r.original_title,
        "poster_path": r.poster_path,
        "backdrop_path": r.backdrop_path,
        "overview": r.overview,
        "release_year": r.release_year,
        "genres": r.genres,
        "status": r.status,
        "rating": r.rating,
        "review_text": r.review_text,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }
