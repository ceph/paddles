from sqlalchemy import Column, Integer, String, Boolean

from paddles.models import Base


class Lab(Base):
    __tablename__ = 'labs'
    id = Column(Integer, primary_key=True)
    name = Column(String(64), default='default', index=True)
    paused = Column(Boolean, default=False)
