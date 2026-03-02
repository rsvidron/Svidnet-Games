"""
Page Access Control model
"""
from sqlalchemy import Column, Integer, String, Boolean, ARRAY, Text
from ..db.base import Base, TimestampMixin, IdMixin


class PageAccess(Base, IdMixin, TimestampMixin):
    """Page Access Control model - manages which roles can access which pages"""

    __tablename__ = "page_access"

    page_name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=False)
    allowed_roles = Column(ARRAY(String), nullable=False, default=["admin"])
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    def __repr__(self):
        return f"<PageAccess(page_name='{self.page_name}', allowed_roles={self.allowed_roles})>"

    def is_accessible_by(self, user_role: str) -> bool:
        """Check if a given role can access this page"""
        return self.is_active and user_role in self.allowed_roles
