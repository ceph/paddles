from sqlalchemy.orm import DeclarativeBase

TEUTHOLOGY_TIMESTAMP_FMT = "%Y-%m-%d_%H:%M:%S"


class Base(DeclarativeBase):
    def slice(self, fields_str):
        sep = ","
        fields = fields_str.strip(sep).split(sep)

        obj_slice = dict()
        for field in fields:
            if field.startswith("_"):
                continue
            value = getattr(self, field)
            if callable(value):
                continue
            obj_slice[field] = value
        return obj_slice


from .runs import Run  # noqa
from .jobs import Job  # noqa
from .nodes import Node  # noqa
from .queue import Queue  # noqa
