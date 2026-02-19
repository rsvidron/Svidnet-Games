"""
Ranked list endpoints — create collections and rank movies/TV shows within them.
"""
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session
from sqlalchemy import asc
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel
from jose import jwt, JWTError
import httpx
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from models.ranked_list import RankedList, RankedListItem

router = APIRouter(prefix="/api/rankings", tags=["rankings"])

TMDB_BEARER = os.getenv(
    "TMDB_BEARER_TOKEN",
    "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiI2ZjRlMGZhZWJjZTY3Yjk4NzYxMmIxZmZjZmI3ODg1ZSIsIm5iZiI6MTcyMjQ0MzkzMi43OTcsInN1YiI6IjY2YWE2ODljNTliYWI3OGRiNzBhZjhiNSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.4Y4Lu7P-vaFpK07YlMutOHD5yuk4iATpWF28K4yapTQ"
)
TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_HEADERS = {"Authorization": f"Bearer {TMDB_BEARER}", "accept": "application/json"}


# ── DB ────────────────────────────────────────────────────────────────────────
def get_db():
    from database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Auth ──────────────────────────────────────────────────────────────────────
def get_current_user_id(authorization: Optional[str] = Header(None)) -> int:
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.removeprefix("Bearer ").strip()
    secret = os.getenv("SECRET_KEY", "test-secret-key-for-development")
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        user_id = payload.get("sub")
        if user_id is None:
            user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token claims")
        return int(user_id)
    except HTTPException:
        raise
    except JWTError as e:
        print(f"[rankings] JWT error: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    except Exception as e:
        print(f"[rankings] Auth error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ── Schemas ───────────────────────────────────────────────────────────────────
class ListCreate(BaseModel):
    title: str
    description: Optional[str] = None
    is_public: bool = False


class ListUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None


class ItemAdd(BaseModel):
    media_id: str
    media_type: str          # "movie" or "tv"
    title: str
    poster_path: Optional[str] = None
    release_year: Optional[str] = None
    overview: Optional[str] = None
    note: Optional[str] = None


class ItemUpdate(BaseModel):
    note: Optional[str] = None


class ReorderBody(BaseModel):
    # Ordered list of item IDs from rank 1 → N
    item_ids: List[int]


# ── List CRUD ─────────────────────────────────────────────────────────────────
@router.get("/my")
def get_my_lists(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Return all ranked lists owned by the current user."""
    lists = db.query(RankedList).filter(RankedList.user_id == user_id).order_by(RankedList.updated_at.desc()).all()
    return [_list_dict(lst, db) for lst in lists]


@router.post("/my")
def create_list(
    body: ListCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Create a new ranked list."""
    lst = RankedList(
        user_id=user_id,
        title=body.title,
        description=body.description,
        is_public=body.is_public,
    )
    db.add(lst)
    db.commit()
    db.refresh(lst)
    return _list_dict(lst, db)


@router.get("/my/{list_id}")
def get_list(
    list_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Return a single list with all its ranked items."""
    lst = _get_owned_list(list_id, user_id, db)
    items = db.query(RankedListItem).filter(
        RankedListItem.list_id == list_id
    ).order_by(asc(RankedListItem.rank)).all()
    result = _list_dict(lst, db)
    result["items"] = [_item_dict(i) for i in items]
    return result


@router.patch("/my/{list_id}")
def update_list(
    list_id: int,
    body: ListUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Update list title, description, or visibility."""
    lst = _get_owned_list(list_id, user_id, db)
    if body.title is not None:
        lst.title = body.title
    if body.description is not None:
        lst.description = body.description
    if body.is_public is not None:
        lst.is_public = body.is_public
    lst.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(lst)
    return _list_dict(lst, db)


@router.delete("/my/{list_id}")
def delete_list(
    list_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Delete a list and all its items."""
    lst = _get_owned_list(list_id, user_id, db)
    db.delete(lst)
    db.commit()
    return {"ok": True}


# ── Item CRUD ─────────────────────────────────────────────────────────────────
@router.post("/my/{list_id}/items")
def add_item(
    list_id: int,
    body: ItemAdd,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Add a movie/TV show to a ranked list. Appended at the bottom."""
    _get_owned_list(list_id, user_id, db)

    # Check not already in the list
    existing = db.query(RankedListItem).filter(
        RankedListItem.list_id == list_id,
        RankedListItem.media_id == body.media_id,
        RankedListItem.media_type == body.media_type,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Already in this list")

    # Next rank = current max + 1
    max_rank = db.query(RankedListItem).filter(
        RankedListItem.list_id == list_id
    ).count()

    item = RankedListItem(
        list_id=list_id,
        rank=max_rank + 1,
        media_id=body.media_id,
        media_type=body.media_type,
        title=body.title,
        poster_path=body.poster_path,
        release_year=body.release_year,
        overview=body.overview,
        note=body.note,
    )
    db.add(item)

    # Touch parent list updated_at
    lst = db.query(RankedList).filter(RankedList.id == list_id).first()
    lst.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    return _item_dict(item)


@router.patch("/my/{list_id}/items/{item_id}")
def update_item(
    list_id: int,
    item_id: int,
    body: ItemUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Update a per-item note."""
    _get_owned_list(list_id, user_id, db)
    item = db.query(RankedListItem).filter(
        RankedListItem.id == item_id,
        RankedListItem.list_id == list_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if body.note is not None:
        item.note = body.note
    db.commit()
    db.refresh(item)
    return _item_dict(item)


@router.delete("/my/{list_id}/items/{item_id}")
def remove_item(
    list_id: int,
    item_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Remove an item and re-pack ranks so they stay contiguous."""
    _get_owned_list(list_id, user_id, db)
    item = db.query(RankedListItem).filter(
        RankedListItem.id == item_id,
        RankedListItem.list_id == list_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    removed_rank = item.rank
    db.delete(item)

    # Shift everything below up by 1
    remaining = db.query(RankedListItem).filter(
        RankedListItem.list_id == list_id,
        RankedListItem.rank > removed_rank,
    ).all()
    for r in remaining:
        r.rank -= 1

    lst = db.query(RankedList).filter(RankedList.id == list_id).first()
    lst.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}


@router.put("/my/{list_id}/reorder")
def reorder_items(
    list_id: int,
    body: ReorderBody,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Reorder items by supplying the full ordered list of item IDs.
    The first ID gets rank 1, second gets rank 2, etc.
    """
    _get_owned_list(list_id, user_id, db)
    items = db.query(RankedListItem).filter(RankedListItem.list_id == list_id).all()
    item_map = {i.id: i for i in items}

    if set(body.item_ids) != set(item_map.keys()):
        raise HTTPException(status_code=400, detail="item_ids must contain all items in the list")

    for rank, item_id in enumerate(body.item_ids, start=1):
        item_map[item_id].rank = rank

    lst = db.query(RankedList).filter(RankedList.id == list_id).first()
    lst.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}


# ── TMDB search proxy (reused from reviews, keeps rankings self-contained) ────
@router.get("/search")
async def search_media(
    q: str = Query(..., min_length=1),
    media_type: str = Query("multi", regex="^(multi|movie|tv)$"),
):
    url = f"{TMDB_BASE}/search/{'multi' if media_type == 'multi' else media_type}"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers=TMDB_HEADERS, params={"query": q, "include_adult": False})
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="TMDB search failed")
    data = resp.json()
    results = []
    for item in data.get("results", []):
        mt = item.get("media_type", media_type)
        if mt not in ("movie", "tv"):
            continue
        is_movie = mt == "movie"
        title = item.get("title") if is_movie else item.get("name")
        date_str = item.get("release_date") if is_movie else item.get("first_air_date")
        results.append({
            "id": str(item["id"]),
            "media_type": mt,
            "title": title,
            "poster_path": item.get("poster_path"),
            "release_year": date_str[:4] if date_str else None,
            "overview": item.get("overview"),
        })
    return {"results": results[:20]}


# ── Helpers ───────────────────────────────────────────────────────────────────
def _get_owned_list(list_id: int, user_id: int, db: Session) -> RankedList:
    lst = db.query(RankedList).filter(RankedList.id == list_id).first()
    if not lst:
        raise HTTPException(status_code=404, detail="List not found")
    if lst.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not your list")
    return lst


def _list_dict(lst: RankedList, db: Session) -> dict:
    count = db.query(RankedListItem).filter(RankedListItem.list_id == lst.id).count()
    # Grab first 4 posters for the cover mosaic
    top_items = db.query(RankedListItem).filter(
        RankedListItem.list_id == lst.id,
        RankedListItem.poster_path.isnot(None),
    ).order_by(asc(RankedListItem.rank)).limit(4).all()
    return {
        "id": lst.id,
        "title": lst.title,
        "description": lst.description,
        "is_public": lst.is_public,
        "item_count": count,
        "cover_posters": [i.poster_path for i in top_items],
        "created_at": lst.created_at.isoformat() if lst.created_at else None,
        "updated_at": lst.updated_at.isoformat() if lst.updated_at else None,
    }


def _item_dict(i: RankedListItem) -> dict:
    return {
        "id": i.id,
        "list_id": i.list_id,
        "rank": i.rank,
        "media_id": i.media_id,
        "media_type": i.media_type,
        "title": i.title,
        "poster_path": i.poster_path,
        "release_year": i.release_year,
        "overview": i.overview,
        "note": i.note,
        "added_at": i.added_at.isoformat() if i.added_at else None,
    }
