from datetime import datetime
import re
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship, backref
from sqlalchemy.orm.exc import DetachedInstanceError
from sqlalchemy import DateTime
from pecan import conf
from paddles.models import Base
from paddles.models.jobs import Job

suite_names = ['big',
               'ceph-deploy',
               'dummy',
               'experimental',
               'fs',
               'hadoop',
               'iozone',
               'kcephfs',
               'krbd',
               'marginal',
               'mixed-clients',
               'nfs',
               'powercycle',
               'rados',
               'rbd',
               'rgw',
               'samba',
               'smoke',
               'stress',
               'tgt',
               'upgrade-cuttlefish',
               'upgrade-dumpling',
               'upgrade-fs',
               'upgrade-mixed-cluster',
               'upgrade-mixed-mons',
               'upgrade-parallel',
               'upgrade-rados-double',
               'upgrade-rados',
               'upgrade-rbd-double',
               'upgrade-rbd',
               'upgrade-rgw-double',
               'upgrade-rgw',
               'upgrade-small',
               'upgrade',
               ]


def get_name_regexes(timestamp_regex, suite_names):
    """
    Build a regex used for getting timestamp, suite and branch info out of a
    test name.  Typical run names are of the format:
        user-timestamp-suite-branch-flavor-machine_type

    But sometimes suite, or branch, or both, are hyphenated. Unfortunately the
    delimiter is the same character, so for now we build this regex using the
    list of current suites. If this regex doesn't match, Run._parse_name() uses
    a backup regex.
    """
    regex_templ_no_mtype = \
        '(?P<user>.*)-(?P<scheduled>{time})-(?P<suite>{suites})-(?P<branch>.*)-.*?-.*?'  # noqa
    regex_templ = regex_templ_no_mtype + '-(?P<machine_type>.+)'

    # Append '[^-]*' to each suite name to handle suite slices like
    # 'rados:thrash'
    modded_names = [name + '[^-]*' for name in suite_names]
    suites_str = '({names_str})'.format(names_str='|'.join(modded_names))
    return [templ.format(time=timestamp_regex, suites=suites_str)
            for templ in (regex_templ, regex_templ_no_mtype)]


class Run(Base):
    timestamp_regex = \
        '[0-9]{1,4}-[0-9]{1,2}-[0-9]{1,2}_[0-9]{1,2}:[0-9]{1,2}:[0-9]{1,2}'
    timestamp_format = '%Y-%m-%d_%H:%M:%S'
    name_regexes = get_name_regexes(timestamp_regex, suite_names)
    backup_name_regex = '(?P<user>.*)-(?P<scheduled>%s)-(?P<suite>.*)-(?P<branch>.*)-.*?-.*?-(?P<machine_type>.*?)' % timestamp_regex  # noqa

    __tablename__ = 'runs'
    id = Column(Integer, primary_key=True)
    name = Column(String(512), unique=True)
    status = Column(String(16), index=True)
    user = Column(String(32), index=True)
    scheduled = Column(DateTime, index=True)
    suite = Column(String(64), index=True)
    branch = Column(String(64), index=True)
    machine_type = Column(String(32), index=True)
    posted = Column(DateTime, index=True)
    jobs = relationship('Job',
                        backref=backref('run'),
                        cascade='all,delete',
                        lazy='dynamic',
                        order_by='Job.job_id',
                        )

    def __init__(self, name):
        self.name = name
        self.posted = datetime.utcnow()
        parsed_name = self._parse_name()
        self.user = parsed_name.get('user', '')
        self.scheduled = parsed_name.get('scheduled', self.posted)
        self.suite = parsed_name.get('suite', '')
        self.branch = parsed_name.get('branch', '')
        self.machine_type = parsed_name.get('machine_type', '')
        self.set_status()

    def __repr__(self):
        try:
            return '<Run %r>' % self.name
        except DetachedInstanceError:
            return '<Run detached>'

    def __json__(self):
        results = self.get_results()
        status = self.status
        return dict(
            name=self.name,
            href=self.href,
            user=self.user,
            status=status,
            results=results,
            jobs_count=results['total'],
            posted=self.posted,
            scheduled=self.scheduled,
            branch=self.branch,
            suite=self.suite,
            machine_type=self.machine_type,
        )

    def _parse_name(self):
        name_match = re.match(self.name_regexes[0], self.name) or \
            re.match(self.name_regexes[1], self.name) or \
            re.match(self.backup_name_regex, self.name)
        if name_match:
            match_dict = name_match.groupdict()
            scheduled = datetime.strptime(match_dict['scheduled'],
                                          self.timestamp_format)
            return dict(
                user=match_dict['user'].strip(' -'),
                scheduled=scheduled,
                suite=match_dict['suite'].strip(' -'),
                branch=match_dict['branch'].strip(' -'),
                machine_type=match_dict.get('machine_type', '').strip(' -'),
                )
        return dict()

    def get_jobs(self):
        return [job for job in self.jobs]

    def get_jobs_by_description(self):
        jobs = self.get_jobs()
        by_desc = {}
        for job in jobs:
            by_desc[job.description] = job
        return by_desc

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
        jobs_status = [value[0] for value in self.jobs.values(Job.status)]
        passing = jobs_status.count('pass')
        running = jobs_status.count('running')
        fail = jobs_status.count('fail')
        dead = jobs_status.count('dead')
        unknown = jobs_status.count(None) + jobs_status.count('unknown')
        total = self.jobs.count()
        return {
            'pass': passing,
            'running': running,
            'fail': fail,
            'dead': dead,
            'unknown': unknown,
            'total': total
        }

    def set_status(self):
        # Possible values for Run.status are:
        #
        # 'empty', 'running', 'finished dead', 'finished fail',
        # 'finished pass', 'unknown'
        if not self.jobs.count():
            self.status = 'empty'
            return self.status

        old_status = self.status

        results = self.get_results()
        total = results['total']

        # any running => running
        if results['running'] > 0:
            new_status = 'running'
        # all dead => dead
        elif results['dead'] == total:
            new_status = 'finished dead'
        # any fail => fail
        elif results['fail'] > 0:
            new_status = 'finished fail'
        # any dead => fail
        elif results['dead'] > 0:
            new_status = 'finished fail'
        # all passing => pass
        elif results['pass'] == total:
            new_status = 'finished pass'
        # this should not happen
        else:
            new_status = 'unknown'

        if not old_status == new_status:
            self.status = new_status
        return new_status
