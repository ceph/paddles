from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm.exc import DetachedInstanceError
from sqlalchemy.orm import relationship, backref
from paddles.models import Base
from paddles.models.types import JSONType


class Job(Base):

    __tablename__ = 'jobs'
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey('runs.id'))
    run = relationship('Run', backref=backref('jobs', lazy='dynamic'))

    archive_path = Column(String(256))
    description = Column(String(128))
    duration = Column(Integer)
    email = Column(String(64))
    flavor = Column(String(64))
    job_id = Column(String(32))
    kernel = Column(JSONType())
    last_in_suite = Column(Boolean())
    machine_type = Column(String(32))
    name = Column(String(128))
    nuke_on_error = Column(Boolean())
    os_type = Column(String(16))
    overrides = Column(JSONType())
    owner = Column(String(64))
    pid = Column(String(16))
    roles = Column(JSONType())
    success = Column(Boolean())
    targets = Column(JSONType())
    tasks = Column(JSONType())
    teuthology_branch = Column(String(16))
    verbose = Column(Boolean())

    allowed_keys = (
        "archive_path",
        "description",
        "duration",
        "email",
        "flavor",
        "job_id",
        "kernel",
        "last_in_suite",
        "machine_type",
        "name",
        "nuke_on_error",
        "os_type",
        "overrides",
        "owner",
        "pid",
        "roles",
        "success",
        "targets",
        "tasks",
        "teuthology_branch",
        "verbose",
    )

    def __init__(self, json_data, run):
        self.run = run
        self.set_or_update(json_data)

    def set_or_update(self, json_data):
        for k, v in json_data.items():
            key = k.replace('-', '_')
            if key in self.allowed_keys:
                setattr(self, key, v)

    def update(self, json_data):
        self.set_or_update(json_data)

    def __repr__(self):
        try:
            return '<Run %r>' % self.job_id
        except DetachedInstanceError:
            return '<Run detached>'

    def __json__(self):
        json_ = dict()
        for key in self.allowed_keys:
            json_[key] = getattr(self, key)

        return json_
