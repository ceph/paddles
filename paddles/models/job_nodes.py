from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    Table,
)

from paddles.models import Base

job_nodes_table = Table(
    "job_nodes",
    Base.metadata,
    Column("node_id", Integer, ForeignKey("nodes.id"), primary_key=True, index=True),
    Column("job_id", Integer, ForeignKey("jobs.id"), primary_key=True, index=True),
)
