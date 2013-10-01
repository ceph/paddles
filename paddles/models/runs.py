from datetime import datetime
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm.exc import DetachedInstanceError
from sqlalchemy import DateTime
from pecan import conf
from paddles.models import Base


class Run(Base):

    __tablename__ = 'runs'
    id = Column(Integer, primary_key=True)
    name = Column(String(512))
    timestamp = Column(DateTime)

    def __init__(self, name):
        self.name = name
        self.timestamp = datetime.utcnow()

    def __repr__(self):
        try:
            return '<Run %r>' % self.name
        except DetachedInstanceError:
            return '<Run detached>'

    def __json__(self):
        return dict(
            name = self.name,
            jobs = self.get_jobs(),
            href = self.href,
            status = self.status,
            results = self.get_results(),
        )

    @property
    def href(self):
        return "%s/runs/%s/" % (conf.address, self.name),

    def get_results(self):
        passing = self.jobs.filter_by(success=True).count()
        running = self.jobs.filter_by(success=None).count()
        fail = self.jobs.filter_by(success=False).count()
        return {
            'pass': passing,
            'running': running,
            'fail': fail
        }

    def get_jobs(self):
        return [
            {
                'job_id': job.job_id,
                'href': job.href
            }
            for job in self.jobs
        ]

    @property
    def status(self):
        running = self.jobs.filter_by(success=None).count()
        if running:
            return "running"
        return "finished"
