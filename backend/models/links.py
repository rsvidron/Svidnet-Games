from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from database import Base

class Link(Base):
    __tablename__ = "links"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    url = Column(String(2048), nullable=False)
    description = Column(String(500), nullable=True)
    icon = Column(String(10), nullable=True)          # emoji icon
    category = Column(String(100), nullable=True)     # grouping label
    is_active = Column(Boolean, default=True, nullable=False)
    open_in_new_tab = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
