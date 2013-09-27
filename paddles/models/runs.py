from sqlalchemy import Column, Integer, String
from sqlalchemy.orm.exc import DetachedInstanceError
from paddles.models import Base


class Run(Base):

    __tablename__ = 'runs'
    id = Column(Integer, primary_key=True)
    name = Column(String(128))

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        try:
            return '<Run %r>' % self.name
        except DetachedInstanceError:
            return '<Run detached>'

    def __json__(self):
        return dict(
            name = self.name,
            jobs = [job for job in self.jobs],
        )
