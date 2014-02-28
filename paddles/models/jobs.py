from datetime import datetime
from sqlalchemy import (Column, Integer, String, Boolean, ForeignKey, DateTime,
                        Text)
from sqlalchemy.orm.exc import DetachedInstanceError
from pecan import conf
from paddles.models import Base
from paddles.models.types import JSONType


class Job(Base):

    __tablename__ = 'jobs'
    id = Column(Integer, primary_key=True)
    posted = Column(DateTime, index=True)
    updated = Column(DateTime, index=True)
    run_id = Column(Integer, ForeignKey('runs.id', ondelete='CASCADE'))
    status = Column(String(32), index=True)

    archive_path = Column(String(512))
    description = Column(String(512))
    duration = Column(Integer)
    email = Column(String(128))
    failure_reason = Column(Text)
    flavor = Column(String(128))
    job_id = Column(String(32), index=True)
    kernel = Column(JSONType())
    last_in_suite = Column(Boolean())
    machine_type = Column(String(32))
    name = Column(String(512))
    nuke_on_error = Column(Boolean())
    os_type = Column(String(32))
    overrides = Column(JSONType())
    owner = Column(String(128))
    pid = Column(String(32))
    roles = Column(JSONType())
    sentry_event = Column(String(128))
    success = Column(Boolean(), index=True)
    targets = Column(JSONType())
    tasks = Column(JSONType())
    teuthology_branch = Column(String(32))
    verbose = Column(Boolean())

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
        "overrides",
        "owner",
        "pid",
        "roles",
        "sentry_event",
        "status",
        "success",
        "targets",
        "tasks",
        "teuthology_branch",
        "verbose",
    )

    def __init__(self, json_data, run):
        self.run = run
        self.posted = datetime.utcnow()
        self.set_or_update(json_data)

    def set_or_update(self, json_data):
        self.__changed = False
        status_map = {True: 'pass',
                      False: 'fail',
                      None: 'unknown',
                      }
        success_map = {'pass': True,
                       'fail': False,
                       'dead': False,
                       'running': None,
                       }

        if 'status' in json_data:
            status = json_data.pop('status')
            if status == 'dead' and self.success is not None:
                self.update_attr('status', status_map.get(self.success))
            else:
                self.update_attr('status', status)
                json_data['success'] = success_map.get(status)
        elif 'success' in json_data:
            success = json_data.pop('success')
            self.update_attr('status', status_map.get(success))
            self.update_attr('success', success)
        else:
            self.update_attr('status', 'unknown')
            self.update_attr('success', None)

        for k, v in json_data.items():
            key = k.replace('-', '_')
            # Handle teuthology transition from sentry_events -> sentry_event
            if key == 'sentry_events' and v != []:
                key = 'sentry_event'
                v = v[0]
            if key in self.allowed_keys:
                self.update_attr(key, v)
        if self.__changed:
            self.updated = datetime.utcnow()
        if self.job_status_will_change_run_status():
            self.run.set_status()

    def update_attr(self, attr_name, new_value):
        """
        Compare getattr(self, attr_name) with new_value. If equal, do nothing.
        Else, set self.__changed to True and update the value.

        This is used by set_or_update() to determine whethor or not
        self.updated should be... updated.
        """
        if getattr(self, attr_name) != new_value:
            setattr(self, attr_name, new_value)
            self.__changed = True

    def job_status_will_change_run_status(self):
        # Attempt to determine if the job status will require an updated run
        # status
        if self.status is None:
            return False
        elif self.status in self.run.status:
            return False
        else:
            return True

    def update(self, json_data):
        self.set_or_update(json_data)

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
            return '<Job %r>' % self.job_id
        except DetachedInstanceError:
            return '<Job detached>'

    def __json__(self):
        json_ = dict(
            log_href=self.log_href
        )
        for key in self.allowed_keys + ('posted', 'updated'):
            json_[key] = getattr(self, key)

        return json_
