from datetime import datetime
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship, backref
from sqlalchemy.orm.exc import DetachedInstanceError
from sqlalchemy import DateTime
from pecan import conf
from paddles.models import Base


class Run(Base):

    __tablename__ = 'runs'
    id = Column(Integer, primary_key=True)
    name = Column(String(512))
    timestamp = Column(DateTime, index=True)
    jobs = relationship('Job',
                        backref=backref('run'),
                        cascade='all,delete',
                        lazy='dynamic',
                        )

    def __init__(self, name):
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
            name = self.name,
            href = self.href,
            status = status,
            results = results,
        )

    def get_jobs(self):
        return [job for job in self.jobs]

    @property
    def href(self):
        return "%s/runs/%s/" % (conf.address, self.name),

    def get_results(self):
        jobs_success = [job.success for job in self.jobs]
        passing = jobs_success.count(True)
        running = jobs_success.count(None)
        fail = jobs_success.count(False)
        return {
            'pass': passing,
            'running': running,
            'fail': fail
        }

    @property
    def status(self):
        running = self.jobs.filter_by(success=None).count()
        if running:
            return "running"
        return "finished"
