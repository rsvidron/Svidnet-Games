from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base


class Collection(Base):
    """Admin-created canonical collection (e.g. 'Marvel Cinematic Universe').
    Users can create their own personal ranking of any collection."""
    __tablename__ = "collections"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    cover_poster = Column(String(500), nullable=True)   # representative poster path
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CollectionItem(Base):
    """A movie/TV show that belongs to an admin collection."""
    __tablename__ = "collection_items"

    id = Column(Integer, primary_key=True, index=True)
    collection_id = Column(Integer, ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, index=True)
    sort_order = Column(Integer, nullable=False, default=0)  # suggested order within the collection

    # Cached TMDB metadata
    media_id = Column(String(50), nullable=False)
    media_type = Column(String(10), nullable=False)   # "movie" or "tv"
    title = Column(String(500), nullable=False)
    poster_path = Column(String(500), nullable=True)
    release_year = Column(String(10), nullable=True)
    overview = Column(Text, nullable=True)
