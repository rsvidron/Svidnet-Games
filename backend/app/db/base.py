"""
SQLAlchemy base class and common mixins
"""
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, DateTime
from datetime import datetime

Base = declarative_base()


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps"""

    created_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )


class IdMixin:
    """Mixin for primary key id"""

    id = Column(Integer, primary_key=True, index=True)
