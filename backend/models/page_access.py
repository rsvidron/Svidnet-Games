"""
Page Access Control model for oauth_server
"""
from sqlalchemy import Column, Integer, String, Boolean, ARRAY, Text, DateTime
from datetime import datetime
from database import Base


class PageAccess(Base):
    """Page Access Control model - manages which roles can access which pages"""

    __tablename__ = "page_access"

    id = Column(Integer, primary_key=True, index=True)
    page_name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=False)
    allowed_roles = Column(ARRAY(String), nullable=False, default=["admin"])
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<PageAccess(page_name='{self.page_name}', allowed_roles={self.allowed_roles})>"

    def is_accessible_by(self, user_role: str) -> bool:
        """Check if a given role can access this page"""
        return self.is_active and user_role in self.allowed_roles
