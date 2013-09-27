from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm.exc import DetachedInstanceError
from sqlalchemy.orm import relationship, backref
from paddles.models import Base
from paddles.models.types import JSONType


class Job(Base):

    __tablename__ = 'jobs'
    id = Column(Integer, primary_key=True)
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
    run_id = Column(Integer, ForeignKey('runs.id'))
    run = relationship('Run', backref=backref('jobs', lazy='dynamic'))

    def __init__(self, json_data):
        for k, v in json_data.items():
            key = k.replace('-', '_')
            setattr(self, key, v)

    def __repr__(self):
        try:
            return '<Run %r>' % self.username
        except DetachedInstanceError:
            return '<Run detached>'

    def __json__(self):
        return dict(
            name = self.name,
            email = self.email,
            archive_path = self.archive_path,
            description = self.description,
            duration = self.duration,
            flavor = self.flavor,
            job_id = self.job_id,
            kernel = self.kernel,
            last_in_suite = self.last_in_suite,
            machine_type = self.machine_type,
            nuke_on_error = self.nuke_on_error,
            os_type = self.os_type,
            overrides = self.overrides,
            owner = self.owner,
            pid = self.pid,
            roles = self.roles,
            success = self.success,
            targets = self.targets,
            tasks = self.tasks,
            teuthology_branch = self.teuthology_branch,
            verbose = self.verbose,
        )

