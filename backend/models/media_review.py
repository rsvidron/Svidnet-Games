from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base


class MediaReview(Base):
    __tablename__ = "media_reviews"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # External API identifiers
    media_id = Column(String(50), nullable=False)       # TMDB/TVDB ID
    media_type = Column(String(10), nullable=False)     # "movie" or "tv"
    source = Column(String(10), nullable=False, default="tmdb")  # "tmdb" or "tvdb"

    # Cached metadata from API
    title = Column(String(500), nullable=False)
    original_title = Column(String(500), nullable=True)
    poster_path = Column(String(500), nullable=True)
    backdrop_path = Column(String(500), nullable=True)
    overview = Column(Text, nullable=True)
    release_year = Column(String(10), nullable=True)
    genres = Column(String(500), nullable=True)         # comma-separated

    # User review data
    status = Column(String(20), nullable=False, default="watchlist")  # watchlist / watched / dropped
    rating = Column(Integer, nullable=True)             # 1-10
    review_text = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
