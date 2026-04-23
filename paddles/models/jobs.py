import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from pecan import conf

# pre 2.x
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
    select,
)

## 2.x
from sqlalchemy.orm import (
    LoaderCallableStatus,
    Mapped,
    deferred,
    load_only,
    mapped_column,
    relationship,
    validates,
)
from sqlalchemy.orm.exc import DetachedInstanceError, NoResultFound

from paddles.models import TEUTHOLOGY_TIMESTAMP_FMT, Base, Session
from paddles.models.nodes import Node
from paddles.models.types import JSONType
from paddles.util import local_datetime_to_utc

from .job_nodes import job_nodes_table

if TYPE_CHECKING:
    from paddles.models import Run

log = logging.getLogger(__name__)


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("run_id", "job_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    posted: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=True)
    started: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=True)
    updated: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=True)
    run_id: Mapped[datetime] = mapped_column(
        Integer, ForeignKey("runs.id", ondelete="CASCADE"), index=True, nullable=True
    )
    run: Mapped["Run"] = relationship(
        "Run",
        back_populates="jobs",
    )
    status: Mapped[Optional[str]] = mapped_column(String(32), index=True)

    archive_path: Mapped[str] = mapped_column(String(512), nullable=True)
    description: Mapped[str] = deferred(mapped_column(Text))
    duration = mapped_column(Integer)
    email: Mapped[str] = mapped_column(String(128), nullable=True)
    failure_reason: Mapped[str] = deferred(mapped_column(Text))
    flavor: Mapped[str] = mapped_column(String(128), nullable=True)
    job_id: Mapped[str | None] = mapped_column(String(32), index=True, nullable=False)
    kernel = deferred(mapped_column(JSONType()))
    last_in_suite = mapped_column(Boolean())
    machine_type: Mapped[str] = mapped_column(String(32), nullable=True)
    name: Mapped[str] = mapped_column(String(512), nullable=True)
    nuke_on_error = mapped_column(Boolean())
    os_type: Mapped[str] = mapped_column(String(32), nullable=True)
    os_version: Mapped[str] = mapped_column(String(16), nullable=True)
    overrides = deferred(mapped_column(JSONType()))
    owner = mapped_column(String(128))
    priority = mapped_column(Integer, index=True)
    pid = mapped_column(String(32))
    repo = mapped_column(String(256))
    roles = deferred(mapped_column(JSONType()))
    sentry_event = mapped_column(String(128))
    success = mapped_column(Boolean(), index=True)
    branch = mapped_column(String(64), index=True)
    seed = mapped_column(String(32))
    sha1 = mapped_column(String(40), index=True)
    sleep_before_teardown = mapped_column(Integer)
    subset = mapped_column(String(32))
    suite = mapped_column(String(256))
    suite_branch = mapped_column(String(64), index=True)
    suite_path = mapped_column(String(256))
    suite_relpath = mapped_column(String(256))
    suite_repo = mapped_column(String(256))
    suite_sha1 = mapped_column(String(40), index=True)
    targets = deferred(mapped_column(JSONType()))
    target_nodes = relationship(
        "Node",
        secondary=job_nodes_table,
        back_populates="jobs",
        remote_side="Node.id",
    )
    tasks = deferred(mapped_column(JSONType()))
    teuthology_branch = mapped_column(String(64))
    teuthology_sha1 = mapped_column(String(40), index=True)
    timestamp = mapped_column(DateTime)
    user = mapped_column(String(64))
    verbose = mapped_column(Boolean())
    issue_url = deferred(mapped_column(Text))
    comment = deferred(mapped_column(Text))
    pcp_grafana_url = mapped_column(Text)
    queue = mapped_column(String(32), index=True)

    allowed_statuses = (
        "pass",
        "fail",
        "queued",
        "running",
        "dead",
        "unknown",
        "waiting",
    )

    status_map = {
        True: "pass",
        False: "fail",
        None: "unknown",
    }

    def __init__(self, json_data, run):
        self.run = run
        self.posted = datetime.now(timezone.utc)
        targets = json_data.pop("targets", {})
        updated = json_data.pop("updated", None)
        self.update(json_data)
        if targets:
            self.targets = targets
        if updated:
            self.set_updated(updated)
        else:
            self.updated = datetime.now(timezone.utc)

    def update(self, data):
        data.pop("run", None)
        if status := data.pop("status", None):
            data.pop("success", None)
            self.status = status
        elif (success := data.pop("success", None)) is not None:
            self.success = success
            self.status = self.status_map[success]
        # elif self.status is None:
        #     self.status = "unknown"
        for k, v in data.items():
            key = k.replace("-", "_")
            if key in ["posted", "started", "updated", "run_id"]:
                continue
            try:
                setattr(self, key, v)
            except Exception:
                log.exception(f"{key=} {v=}")
                raise

    def set_updated(self, value: str):
        """
        Given a string in the format of '%Y-%m-%d %H:%M:%S', in the local
        timezone, create a datetime object, convert it to UTC, and store it in
        self.updated.
        """
        self.run.updated = self.updated = local_datetime_to_utc(
            datetime.strptime(value.split(".")[0], "%Y-%m-%d %H:%M:%S")
        )

    @validates("status")
    def validate_status(self, key, status):
        log.info(
            f"validate_status job_id={self.job_id} success={self.success} {status=}"
        )
        if status not in self.allowed_statuses:
            raise ValueError("Job status must be one of: %s" % self.allowed_statuses)
        if self.status in ["pass", "fail"]:
            return self.status
        return status

    @property
    def href(self):
        return ("%s/runs/%s/jobs/%s/" % (conf.address, self.run.name, self.job_id),)

    @property
    def log_href(self):
        return conf.job_log_href_templ.format(
            run_name=self.run.name, job_id=self.job_id
        )

    def __repr__(self):
        try:
            return "<Job %r %r>" % (self.name, self.job_id)
        except DetachedInstanceError:
            return "<Job detached>"

    def __json__(self):
        obj = dict(log_href=self.log_href)
        for field in self.__table__.columns:
            if field.name in ["run_id"]:
                continue
            obj[field.name] = getattr(self, field.name)
        return obj


@event.listens_for(Job.branch, "set")
def branch_cb(target: Job, value, oldvalue, initiator):
    if target.run.branch != value:
        target.run.branch = value


@event.listens_for(Job.suite, "set")
def suite_cb(target: Job, value, oldvalue, initiator):
    if target.run.suite != value:
        target.run.suite = value


@event.listens_for(Job.machine_type, "set")
def machine_type_cb(target: Job, value, oldvalue, initiator):
    if target.run.machine_type != value:
        target.run.machine_type = value


@event.listens_for(Job.status, "set")
def status_cb(target: Job, value, oldvalue, initiator):
    log.info(f"status_cb job_id={target.job_id} {oldvalue=} {value=}")
    if (
        oldvalue in (None, LoaderCallableStatus.NO_VALUE, "queued")
        and value == "running"
    ):
        target.started = datetime.now(timezone.utc)
    if target.run.status != "running":
        target.run.started = target.started


# @event.listens_for(Job.success, "set")
# def success_cb(target: Job, value, oldvalue, initiator):
#     log.info(f"success_cb job_id={target.job_id} {oldvalue=} {value=} {target.status=}")
#     if target.status not in ["dead"]:
#         target.status = Job.status_map[value]


@event.listens_for(Job.timestamp, "set", retval=True)
def timestamp_cb(target: Job, value, oldvalue, initiator):
    return datetime.strptime(
        value,
        TEUTHOLOGY_TIMESTAMP_FMT,
    )


@event.listens_for(Job.updated, "set")
def updated_cb(target: Job, value: datetime, oldvalue, initiator, retval=True):
    if target.run:
        if target.run.updated:
            target.run.updated = max(
                target.run.updated.astimezone(timezone.utc),
                value.astimezone(timezone.utc),
            )
        else:
            target.run.updated = value
    # log.info(
    #     f"updated_cb id={target.id} job_id={target.job_id} {oldvalue=} {value=} {target.status=}"
    # )
    return value


@event.listens_for(Job.targets, "set")
def targets_cb(target: Job, value, oldvalue, initiator):
    if oldvalue == value:
        return
    for name in value.keys():
        name = name.split("@")[-1]
        node_query = (
            select(Node).options(load_only(Node.id, Node.name)).where(Node.name == name)
        )
        try:
            node = Session.scalars(node_query).one()
        except NoResultFound:
            node = Node(name=name, machine_type=target.machine_type)
            Session.add(node)
        if node not in target.target_nodes:
            target.target_nodes.append(node)


# @event.listens_for(Job, "before_update")
# def job_update(mapper, connection, target):
#     log.info(f"job_update {target=}")
#     target.updated = datetime.now(timezone.utc)


@event.listens_for(Job, "init")
def new_job(target, args, kwargs):
    log.info(f"new_job {target=} {args=} {kwargs=}")
    if not args[0].get("updated"):
        target.updated = datetime.now(timezone.utc)
