import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import DateTime, Integer, String, event
from sqlalchemy.orm import Mapped, mapped_column

from paddles.exceptions import ForbiddenRequestError, InvalidRequestError
from paddles.models import Base

log = logging.getLogger(__name__)


class Queue(Base):
    __tablename__ = "queue"
    queue: Mapped[str] = mapped_column(String(32), primary_key=True)
    paused_by: Mapped[str | None] = mapped_column(String(64), index=True)
    paused_since: Mapped[datetime | None] = mapped_column(DateTime)
    pause_duration: Mapped[int | None] = mapped_column(Integer)
    paused_until: Mapped[datetime | None] = mapped_column(DateTime)

    allowed_update_keys = [
        "paused_by",
        "paused_since",
        "paused_until",
    ]

    def __init__(self, queue, paused_by=None, pause_duration=0):
        self.queue = queue
        self.paused_by = paused_by
        self.pause_duration = pause_duration

    def update(self, values):
        """
        :param values: a dict.
        """
        self._check_for_update(values)

        self.pause_duration = values.get("pause_duration")
        for k, v in values.items():
            if k in self.allowed_update_keys:
                setattr(self, k, v)

    def _check_for_update(self, values):
        """
        If the given values are safe, do nothing. If not, raise the appropriate
        exception.
        """
        pausing = False
        if "pause_duration" in values:
            pausing = True
        was_paused = self.paused
        if pausing and was_paused is not None:
            to_pause_for = values.get("paused_by")
            verb = "pause"
            if was_paused == pausing:
                raise ForbiddenRequestError(f"Cannot {verb} an already-{verb}d queue")
            elif not to_pause_for:
                raise InvalidRequestError(f"Cannot {verb} without specifying paused_by")

    # @validates("paused_by")
    # def validate_paused_by(self, key, value):

    @property
    def paused(self):
        if self.paused_until is None:
            return False
        if datetime.now(timezone.utc) > self.paused_until.replace(tzinfo=timezone.utc):
            return False
        return True

    def __json__(self):
        return dict(
            queue=self.queue,
            paused=self.paused,
            paused_by=self.paused_by,
            paused_since=self.paused_since,
            paused_until=self.paused_until,
        )


@event.listens_for(Queue.pause_duration, "set")
def pause_duration_cb(target: Queue, value, oldvalue, initiator):
    log.info(
        f"pause_duration_cb queue={target.queue} {oldvalue=} {value=} {target.paused=}"
    )
    # Queue is currently not paused
    if value and value > 0:
        log.info("pausing")
        target.paused_since = datetime.now(timezone.utc)
        target.paused_until = datetime.now(timezone.utc) + timedelta(
            seconds=float(value)
        )
    else:
        log.info(f"not pausing {value=}")
