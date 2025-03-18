import logging
from datetime import datetime
from sqlalchemy import (Column, Integer, String, Boolean, ForeignKey, DateTime,
                        Table, Text)
from sqlalchemy.orm import backref, deferred, load_only, relationship
from sqlalchemy.orm.exc import DetachedInstanceError, NoResultFound
from pecan import conf
from paddles.models import Base, Session, TEUTHOLOGY_TIMESTAMP_FMT
from paddles.models.nodes import Node
from paddles.models.types import JSONType
from paddles.stats import get_client as get_statsd_client
from paddles.util import local_datetime_to_utc

job_nodes_table = Table(
    'job_nodes',
    Base.metadata,
    Column('node_id', Integer, ForeignKey('nodes.id'), primary_key=True,
           index=True),
    Column('job_id', Integer, ForeignKey('jobs.id'), primary_key=True,
           index=True)
)

log = logging.getLogger(__name__)


class Job(Base):
    __tablename__ = 'jobs'
    id = Column(Integer, primary_key=True)
    posted = Column(DateTime, index=True)
    started = Column(DateTime, index=True)
    updated = Column(DateTime, index=True)
    run_id = Column(Integer, ForeignKey('runs.id', ondelete='CASCADE'),
                    index=True)
    status = Column(String(32), index=True)

    archive_path = Column(String(512))
    description = deferred(Column(Text))
    duration = Column(Integer)
    email = Column(String(128))
    failure_reason = deferred(Column(Text))
    flavor = Column(String(128))
    job_id = Column(String(32), index=True)
    kernel = deferred(Column(JSONType()))
    last_in_suite = Column(Boolean())
    machine_type = Column(String(32))
    name = Column(String(512))
    nuke_on_error = Column(Boolean())
    os_type = Column(String(32))
    os_version = Column(String(16))
    overrides = deferred(Column(JSONType()))
    owner = Column(String(128))
    priority = Column(Integer, index=True)
    pid = Column(String(32))
    repo = Column(String(256))
    roles = deferred(Column(JSONType()))
    sentry_event = Column(String(128))
    success = Column(Boolean(), index=True)
    branch = Column(String(64), index=True)
    seed = Column(String(32))
    sha1 = Column(String(40), index=True)
    sleep_before_teardown = Column(Integer)
    subset = Column(String(32))
    suite = Column(String(256))
    suite_branch = Column(String(64), index=True)
    suite_path = Column(String(256))
    suite_relpath = Column(String(256))
    suite_repo = Column(String(256))
    suite_sha1 = Column(String(40), index=True)
    targets = deferred(Column(JSONType()))
    target_nodes = relationship("Node", secondary=job_nodes_table,
                                backref=backref('jobs'), lazy='dynamic')
    tasks = deferred(Column(JSONType()))
    teuthology_branch = Column(String(64))
    teuthology_sha1 = Column(String(40), index=True)
    timestamp = Column(DateTime)
    user = Column(String(64))
    verbose = Column(Boolean())
    issue_url = deferred(Column(Text))
    comment = deferred(Column(Text))
    pcp_grafana_url = Column(Text)
    queue = Column(String(32), index=True)

    allowed_keys = (
        "archive_path",
        "description",
        "duration",
        "email",
        "failure_reason",
        "flavor",
        "job_id",
        "kernel",
        "last_in_suite",
        "machine_type",
        "name",
        "nuke_on_error",
        "os_type",
        "os_version",
        "overrides",
        "owner",
        "pid",
        "roles",
        "sentry_event",
        "status",
        "success",
        "branch",
        "seed",
        "sha1",
        "subset",
        "suite",
        "suite_branch",
        "suite_path",
        "suite_relpath",
        "suite_repo",
        "suite_sha1",
        "targets",
        "tasks",
        "timestamp",
        "teuthology_branch",
        "verbose",
        "pcp_grafana_url",
        "priority",
        "user",
        "queue",
    )

    allowed_statuses = (
        "pass",
        "fail",
        "queued",
        "running",
        "dead",
        "unknown",
        "waiting",
    )

    def __init__(self, json_data, run):
        self.run = run
        self.posted = datetime.utcnow()
        self.set_or_update(json_data)

    def set_or_update(self, json_data):
        # Set self.updated, and more importantly, self.run.updated, to avoid
        # deadlocks when lots of jobs are updated at once.
        self.run.updated = self.updated = datetime.utcnow()

        if 'timestamp' in json_data:
            self.timestamp = datetime.strptime(
                json_data.pop('timestamp'),
                TEUTHOLOGY_TIMESTAMP_FMT,
            )

        status_map = {True: 'pass',
                      False: 'fail',
                      None: 'unknown',
                      }

        old_status = self.status
        old_run_status = self.run.status
        if 'status' in json_data:
            status = json_data.pop('status')
            if status not in self.allowed_statuses:
                raise ValueError("Job status must be one of: %s" %
                                 self.allowed_statuses)
            if self.status not in ('pass', 'fail'):
                self.status = status
        elif 'success' in json_data:
            success = json_data.pop('success')
            self.status = status_map.get(success)
            self.success = success
        elif self.success is None and self.status is None:
            self.status = 'unknown'

        if old_status in (None, 'queued') and self.status == 'running':
            self.started = datetime.utcnow()

        if self.status != old_status:
            # Submit pass/fail/dead stats to statsd
            if self.status in ('pass', 'fail', 'dead'):
                counter = get_statsd_client().get_counter('jobs.status')
                counter.increment(self.status)
            self.run.set_status()

        if old_run_status != 'running' and self.run.status == 'running':
            self.run.started = self.started

        target_nodes_q = self.target_nodes.options(load_only('id', 'name'))
        target_nodes = target_nodes_q.count()
        if json_data.get('targets') is not None:
            if len(json_data.get('targets', {})) > target_nodes:
                # Populate self.target_nodes, creating Node objects if necessary
                targets = json_data['targets']
                for target_key in targets.keys():
                    if '@' in target_key:
                        hostname = target_key.split('@')[1]
                    else:
                        hostname = target_key
                    node_q = Node.query.options(load_only('id', 'name'))\
                        .filter(Node.name == hostname)
                    try:
                        node = node_q.one()
                    except NoResultFound:
                        node = Node(name=hostname)
                        mtype = json_data.get('machine_type')
                        if mtype:
                            node.machine_type = mtype
                    if node not in self.target_nodes:
                        self.target_nodes.append(node)

        for k, v in json_data.items():
            key = k.replace('-', '_')
            if key == 'updated':
                self.set_updated(v)
                continue
            # Correct potentially-incorrect Run.suite/branch values
            # We started putting the suite/branch names in the job config on
            # 5/1/2014
            elif key == 'suite' and self.run.suite != v:
                self.run.suite = v
            elif key == 'branch' and self.run.branch != v:
                self.run.branch = v
            # Correct a potential 'multi' value parsed from the run name to be
            # equal to the actual value given to the runs
            elif key == 'machine_type' and self.run.machine_type != v:
                self.run.machine_type = v
            if key in self.allowed_keys:
                setattr(self, key, v)

    def set_updated(self, local_str):
        """
        Given a string in the format of '%Y-%m-%d %H:%M:%S', in the local
        timezone, create a datetime object, convert it to UTC, and store it in
        self.updated.
        """
        local_str = local_str.split(".")[0]
        local_dt = datetime.strptime(local_str, '%Y-%m-%d %H:%M:%S')
        utc_dt = local_datetime_to_utc(local_dt)
        self.run.updated = self.updated = utc_dt

    def update(self, json_data):
        self.set_or_update(json_data)
        Session.flush()

    @property
    def href(self):
        return "%s/runs/%s/jobs/%s/" % (conf.address, self.run.name,
                                        self.job_id),

    @property
    def log_href(self):
        return conf.job_log_href_templ.format(run_name=self.run.name,
                                              job_id=self.job_id)

    def __repr__(self):
        try:
            return '<Job %r %r>' % (self.name, self.job_id)
        except DetachedInstanceError:
            return '<Job detached>'

    def __json__(self):
        json_ = dict(
            log_href=self.log_href
        )
        for key in self.allowed_keys + ('posted', 'started', 'updated'):
            json_[key] = getattr(self, key)

        return json_
