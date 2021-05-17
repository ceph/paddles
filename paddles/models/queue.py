import sqlalchemy.exc
from sqlalchemy import (Boolean, Column, DateTime, Integer, String)
from datetime import datetime

from paddles.exceptions import (InvalidRequestError, ForbiddenRequestError)
from paddles.models import Base

import logging
log = logging.getLogger(__name__)

class Queue(Base):

    __tablename__ = 'queue'

    machine_type = Column(String(32), primary_key=True)

    paused = Column(Boolean(), nullable=False, default=False, index=True)
    paused_by = Column(String(64), index=True)
    paused_since = Column(DateTime)
    pause_duration = Column(Integer)

    allowed_update_keys = [
        'paused',
        'paused_by',
        'paused_since',
        'pause_duration',
    ]

    def __init__(self, machine_type, paused=None, paused_by=None, paused_since=None, 
                pause_duration=None):
        self.machine_type = machine_type
        self.paused = paused
        self.paused_by = paused_by
        self.paused_since = paused_since
        self.pause_duration = pause_duration

    def update(self, values):
        """
        :param values: a dict.
        """
        self._check_for_update(values)
        was_paused = self.paused

        for k, v in values.items():
            if k in self.allowed_update_keys:
                setattr(self, k, v)

        if 'paused' in values:
            if self.paused != was_paused:
                self.paused_since = datetime.utcnow() if self.paused else None
            if not self.paused:
                self.paused_by = None

    def _check_for_update(self, values):
        """
        If the given values are safe, do nothing. If not, raise the appropriate
        exception.
        """
        pausing = values.get('paused')
        was_paused = self.paused
        if pausing in (True, False) and was_paused is not None:
            to_pause_for = values.get('paused_by')
            verb = {False: 'unpause', True: 'pause'}.get(pausing)
            if was_paused == pausing:
                raise ForbiddenRequestError(
                    f"Cannot {verb} an already-{verb}d queue")
            elif not to_pause_for:
                raise InvalidRequestError(
                    f"Cannot {verb} without specifying paused_by")
            elif (verb == 'unpause' and was_paused and to_pause_for !=
                  self.paused_by):
                raise ForbiddenRequestError(
                    f"Cannot {verb} - paused_by value must match {self.paused_by}")
        
    
    def __json__(self):
        return dict(
            machine_type = self.machine_type,
            paused = self.paused,
            paused_by = self.paused_by,
            paused_since = self.paused_since,
            pause_duration = self.pause_duration
        )

