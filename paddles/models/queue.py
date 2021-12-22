from sqlalchemy import (Column, DateTime, Integer, String)
from datetime import datetime, timedelta

from paddles.exceptions import (InvalidRequestError, ForbiddenRequestError)
from paddles.models import Base

import logging
log = logging.getLogger(__name__)


class Queue(Base):

    __tablename__ = 'queue'
    queue = Column(String(32), primary_key=True)
    paused_by = Column(String(64), index=True)
    paused_since = Column(DateTime)
    pause_duration = Column(Integer)
    paused_until = Column(DateTime)

    allowed_update_keys = [
        'paused_by',
        'paused_since',
        'paused_until',
    ]

    def __init__(self, queue, paused_by=None, pause_duration=None):
        self.queue = queue
        self.paused_by = paused_by
        self.pause_duration = pause_duration

    def update(self, values):
        """
        :param values: a dict.
        """
        self._check_for_update(values)

        for k, v in values.items():
            if k in self.allowed_update_keys:
                setattr(self, k, v)
        if 'pause_duration' in values:
            pause_duration = values['pause_duration']
            # Queue is currently not paused
            if self.paused is not True:
                self.paused_since = datetime.utcnow()
                self.paused_until = datetime.utcnow() + timedelta(seconds=float(pause_duration))

    def _check_for_update(self, values):
        """
        If the given values are safe, do nothing. If not, raise the appropriate
        exception.
        """
        pausing = False
        if 'pause_duration' in values:
            pausing = True
        was_paused = self.paused
        if pausing and was_paused is not None:
            to_pause_for = values.get('paused_by')
            verb = 'pause'
            if was_paused == pausing:
                raise ForbiddenRequestError(
                    f"Cannot {verb} an already-{verb}d queue")
            elif not to_pause_for:
                raise InvalidRequestError(
                    f"Cannot {verb} without specifying paused_by")

    @property
    def paused(self):
        if self.paused_until is None:
            return False
        if datetime.utcnow() > self.paused_until:
            return False
        return True

    def __json__(self):
        return dict(
            queue=self.queue,
            paused=self.paused,
            paused_by=self.paused_by,
            paused_since=self.paused_since,
            paused_until=self.paused_until
        )
