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

    __tablename__ = 'runs'
    id = Column(Integer, primary_key=True)
    name = Column(String(512))
    timestamp = Column(DateTime, index=True)
    scheduled = Column(DateTime, index=True)
    jobs = relationship('Job',
                        backref=backref('run'),
                        cascade='all,delete',
                        lazy='dynamic',
                        order_by='Job.id',
                        )

    def __init__(self, name):
        # This ought to go at the top of the class declaration, but if we do
        # that we run into an circular import race condition
        if not hasattr(Run, 'timestamp_regex'):
            Run.timestamp_regex = re.compile('(%s)' % conf.timestamp_regex)
            Run.timestamp_format = conf.timestamp_format

        self.name = name
        self.timestamp = datetime.utcnow()

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
            timestamp=self.timestamp,
            scheduled=self.scheduled,
        )

    def get_jobs(self):
        return [job for job in self.jobs]

    @property
    def scheduled(self):
        match = re.search(self.timestamp_regex, self.name)
        if match:
            stamp = match.groups()[0]
            return datetime.strptime(stamp, self.timestamp_format)
        else:
            return self.timestamp

    @property
    def updated(self):
        if self.jobs.count():
            last_updated_job = self.jobs.order_by(Job.updated)[-1]
            return last_updated_job.updated
        else:
            return max(self.scheduled, self.timestamp)

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
