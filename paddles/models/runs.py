from sqlalchemy import Column, Integer, String
from sqlalchemy.orm.exc import DetachedInstanceError
from pecan import conf
from paddles.models import Base


class Run(Base):

    __tablename__ = 'runs'
    id = Column(Integer, primary_key=True)
    name = Column(String(128))

    def __init__(self, name):
        self.name = name

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
        results = {'pass': 0, 'running': 0, 'fail': 0}
        for job in self.jobs:
            if job.success:
                results['pass'] += 1
            elif not job.success:
                results['fail'] += 1
            # TODO determine how we do pending ones
        return results

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
        # TODO We can't determine this until we know
        # about job statuses that tells us they are not
        # done.
        return "finished"
