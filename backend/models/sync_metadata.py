"""
Sync Metadata Model
Tracks when odds were last synced from The Odds API
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from datetime import datetime, timezone
from database import Base


class SyncMetadata(Base):
    """
    Tracks sync operations for the sportsbook
    Only one row should exist in this table
    """
    __tablename__ = "sync_metadata"

    id = Column(Integer, primary_key=True, index=True)
    last_sync_time = Column(DateTime, nullable=True)  # When last sync completed
    sync_status = Column(String(20), default="never", nullable=False)  # success, failed, running, never
    games_synced = Column(Integer, default=0, nullable=False)  # Number of games synced in last run
    error_message = Column(String(500), nullable=True)  # Error details if sync failed
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
