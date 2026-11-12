from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from paddles.models import Base


class RunTag(Base):
    __tablename__ = 'run_tags'
    __table_args__ = (
        UniqueConstraint('run_id', 'tag', name='uq_run_tags_run_id_tag'),
    )

    id = Column(Integer, primary_key=True)
    run_id = Column(
        Integer,
        ForeignKey('runs.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    tag = Column(String(256), nullable=False, index=True)

    run = relationship('Run', back_populates='run_tag_rows')
