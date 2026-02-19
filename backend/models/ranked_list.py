from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base


class RankedList(Base):
    __tablename__ = "ranked_lists"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class RankedListItem(Base):
    __tablename__ = "ranked_list_items"

    id = Column(Integer, primary_key=True, index=True)
    list_id = Column(Integer, ForeignKey("ranked_lists.id", ondelete="CASCADE"), nullable=False, index=True)
    rank = Column(Integer, nullable=False)           # 1-based position

    # Cached TMDB metadata (so we don't need API calls to render the list)
    media_id = Column(String(50), nullable=False)
    media_type = Column(String(10), nullable=False)  # "movie" or "tv"
    title = Column(String(500), nullable=False)
    poster_path = Column(String(500), nullable=True)
    release_year = Column(String(10), nullable=True)
    overview = Column(Text, nullable=True)

    # Optional per-item note
    note = Column(Text, nullable=True)

    added_at = Column(DateTime(timezone=True), server_default=func.now())
