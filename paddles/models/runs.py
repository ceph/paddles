from datetime import datetime
import re
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship, backref
from sqlalchemy.orm.exc import DetachedInstanceError
from sqlalchemy import DateTime
from pecan import conf
from paddles.models import Base
from paddles.models.jobs import Job


class Run(Base):

    # Typical run names are of the format:
    #   user-timestamp-suite-branch-flavor-machine_type
    timestamp_regex = \
        '([0-9]{1,4}-[0-9]{1,2}-[0-9]{1,2}_[0-9]{1,2}:[0-9]{1,2}:[0-9]{1,2})'
    timestamp_format = '%Y-%m-%d_%H:%M:%S'
    suite_regex = '.*-%s-(.*?)-.*-.*?-.*?-.*?' % timestamp_regex
    branch_regex = '.*-%s-.*-(.*)-.*?-.*?-.*?' % timestamp_regex

    __tablename__ = 'runs'
    id = Column(Integer, primary_key=True)
    name = Column(String(512))
    suite = Column(String(64), index=True)
    branch = Column(String(64), index=True)
    posted = Column(DateTime, index=True)
    scheduled = Column(DateTime, index=True)
    jobs = relationship('Job',
                        backref=backref('run'),
                        cascade='all,delete',
                        lazy='dynamic',
                        order_by='Job.id',
                        )

    def __init__(self, name):
        self.name = name
        self.suite = self._parse_suite()
        self.branch = self._parse_branch()
        self.posted = datetime.utcnow()

    def __repr__(self):
        try:
            return '<Run %r>' % self.name
        except DetachedInstanceError:
            return '<Run detached>'

    def __json__(self):
        results = self.get_results()
        status = 'running' if results['running'] else 'finished'
        return dict(
            name=self.name,
            href=self.href,
            status=status,
            results=results,
            jobs_count=results['total'],
            posted=self.posted,
            scheduled=self.scheduled,
        )

    def _parse_suite(self):
        suite_match = re.match(self.suite_regex, self.name)
        if suite_match:
            return suite_match.groups()[1]
        else:
            return ''

    def _parse_branch(self):
        branch_match = re.match(self.branch_regex, self.name)
        if branch_match:
            return branch_match.groups()[1]
        else:
            return ''

    def get_jobs(self):
        return [job for job in self.jobs]

    def get_jobs_by_description(self):
        jobs = self.get_jobs()
        by_desc = {}
        for job in jobs:
            by_desc[job.description] = job
        return by_desc

    @property
    def scheduled(self):
        match = re.search(self.timestamp_regex, self.name)
        if match:
            stamp = match.groups()[0]
            return datetime.strptime(stamp, self.timestamp_format)
        else:
            return self.posted

    @property
    def updated(self):
        if self.jobs.count():
            last_updated_job = self.jobs.order_by(Job.updated)[-1]
            return last_updated_job.updated
        else:
            return max(self.scheduled, self.posted)

    @property
    def href(self):
        return "%s/runs/%s/" % (conf.address, self.name),

    def get_results(self):
        jobs_success = [job.success for job in self.jobs]
        passing = jobs_success.count(True)
        running = jobs_success.count(None)
        fail = jobs_success.count(False)
        total = self.jobs.count()
        return {
            'pass': passing,
            'running': running,
            'fail': fail,
            'total': total
        }

    @property
    def status(self):
        running = self.jobs.filter_by(success=None).count()
        if running:
            return "running"
        return "finished"
