from datetime import datetime
import re
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship, backref
from sqlalchemy.orm.exc import DetachedInstanceError
from sqlalchemy import DateTime
from pecan import conf
from paddles.util import local_datetime_to_utc
from paddles.models import Base, Session
from paddles.models.jobs import Job

suite_names = ['big',
               'ceph-deploy',
               'clusters',
               'dummy',
               'experimental',
               'fs',
               'hadoop',
               'iozone',
               'kcephfs',
               'knfs',
               'krbd',
               'marginal',
               'mixed-clients',
               'mount',
               'multimds',
               'nfs',
               'powercycle',
               'rados',
               'rbd',
               'rest',
               'rgw',
               'samba',
               'smoke',
               'stress',
               'tgt',
               'upgrade:dumpling-x:stress-split',
               'upgrade:dumpling-x',
               'upgrade:dumpling-emperor-x',
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
               'workload',
               ]


machine_types = ['burnupi', 'mira', 'plana', 'saya', 'tala', 'vps']


distros = ['centos', 'debian', 'fedora', 'opensuse', 'rhel', 'suse', 'ubuntu']


def get_name_regexes(timestamp_regex, suite_names, distros, machine_types):
    """
    Build a regex used for getting timestamp, suite and branch info out of a
    test name.  Typical run names are of the format:
        user-timestamp-suite-branch-kernel_branch-flavor-machine_type

    But sometimes suite, or branch, or both, are hyphenated. Unfortunately the
    delimiter is the same character, so for now we build this regex using the
    list of current suites. If this regex doesn't match, Run._parse_name() uses
    a backup regex.
    """
    regex_templ_base = \
        '(?P<user>.*)-(?P<scheduled>{time})-(?P<suite>{suites})-(?P<branch>.+)-(?P<kernel_branch>.+)-(?P<flavor>[^-]+)'  # noqa
    regex_templ_mtype = \
        regex_templ_base + '-(?P<machine_type>{mtypes})'.format(
            mtypes='|'.join(machine_types))
    regex_templ_distro = regex_templ_mtype + '-(?P<distro>({distros}))'.format(
        distros='|'.join(distros))

    # Append '[^-]*' to each suite name to handle suite slices like
    # 'rados:thrash'
    modded_names = [name + '[^-]*' for name in suite_names]
    suites_str = '({names_str})'.format(names_str='|'.join(modded_names))
    return [templ.format(time=timestamp_regex, suites=suites_str)
            for templ in (
                regex_templ_distro + '$',
                regex_templ_mtype + '$',
                regex_templ_base + '$',
            )]


class Run(Base):
    timestamp_regex = \
        '[0-9]{1,4}-[0-9]{1,2}-[0-9]{1,2}_[0-9]{1,2}:[0-9]{1,2}:[0-9]{1,2}'
    timestamp_format = '%Y-%m-%d_%H:%M:%S'
    name_regexes = get_name_regexes(timestamp_regex, suite_names, distros,
                                    machine_types)
    backup_name_regex = '(?P<user>.*)-(?P<scheduled>%s)-(?P<suite>.*)-(?P<branch>.*)-.*?-.*?-(?P<machine_type>.*?)' % timestamp_regex  # noqa

    __tablename__ = 'runs'
    id = Column(Integer, primary_key=True)
    name = Column(String(512), unique=True)
    status = Column(String(16), index=True)
    user = Column(String(32), index=True)
    scheduled = Column(DateTime, index=True)
    suite = Column(String(256), index=True)
    branch = Column(String(128), index=True)
    machine_type = Column(String(32), index=True)
    posted = Column(DateTime, index=True)
    started = Column(DateTime, index=True)
    updated = Column(DateTime, index=True)
    jobs = relationship('Job',
                        backref=backref('run'),
                        cascade='all,delete',
                        lazy='dynamic',
                        order_by='Job.job_id',
                        )

    allowed_statuses = ('empty',
                        'queued',
                        'running',
                        'waiting',
                        'unknown',
                        'finished pass',
                        'finished dead',
                        'finished fail',
                        )

    def __init__(self, name):
        self.name = name
        self.posted = datetime.utcnow()
        parsed_name = self.parse_name()
        self.user = parsed_name.get('user', '')
        if 'scheduled' in parsed_name:
            scheduled_local = parsed_name['scheduled']
            self.scheduled = local_datetime_to_utc(scheduled_local)
        else:
            self.scheduled = self.posted
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
        status = self.set_status(results)
        return dict(
            name=self.name,
            href=self.href,
            user=self.user,
            status=status,
            results=results,
            jobs_count=results['total'],
            posted=self.posted,
            scheduled=self.scheduled,
            started=self.started,
            updated=self.updated,
            branch=self.branch,
            suite=self.suite,
            machine_type=self.machine_type,
            sha1=results['sha1'],
        )

    @classmethod
    def _parse_name(cls, name):
        name_match = re.match(cls.name_regexes[0], name) or \
            re.match(cls.name_regexes[1], name) or \
            re.match(cls.name_regexes[2], name) or \
            re.match(cls.backup_name_regex, name)
        if name_match:
            match_dict = name_match.groupdict()
            for (key, value) in match_dict.items():
                match_dict[key] = value.strip(' -')

            match_dict['scheduled'] = datetime.strptime(
                match_dict['scheduled'], cls.timestamp_format)
            return match_dict
        return dict()

    def parse_name(self):
        return self._parse_name(self.name)

    def get_jobs(self):
        return [job for job in self.jobs]

    def get_jobs_by_description(self):
        jobs = self.get_jobs()
        by_desc = {}
        for job in jobs:
            by_desc[job.description] = job
        return by_desc

    @property
    def _updated(self):
        if self.jobs.count():
            last_updated_job = self.jobs.order_by(Job.updated)[-1]
            return last_updated_job.updated
        else:
            return max(self.scheduled, self.posted)

    @property
    def href(self):
        return "%s/runs/%s/" % (conf.address, self.name),

    def get_results(self):
        with Session.no_autoflush:
            jobs_status = [value[0] for value in self.jobs.values(Job.status)]
            sha1 = next(self.jobs.values(Job.sha1), ['none'])[0]
        queued = jobs_status.count('queued')
        passing = jobs_status.count('pass')
        waiting = jobs_status.count('waiting')
        running = jobs_status.count('running')
        fail = jobs_status.count('fail')
        dead = jobs_status.count('dead')
        unknown = jobs_status.count(None) + jobs_status.count('unknown')
        total = len(jobs_status)
        return {
            'queued': queued,
            'pass': passing,
            'running': running,
            'waiting': waiting,
            'fail': fail,
            'dead': dead,
            'unknown': unknown,
            'total': total,
            'sha1': sha1,
        }

    def set_status(self, results=None):
        """
        Calculate the run's status based on the status of its jobs.

        :param results: Not required. The return value from self.get_results().
        """
        results = results or self.get_results()
        if results['total'] == 0:
            self.status = 'empty'
            return self.status

        old_status = self.status

        total = results['total']

        # all queued => queued
        if results['queued'] == total:
            new_status = 'queued'
        # any running => running
        elif results['running'] > 0:
            new_status = 'running'
        # any waiting => waiting
        elif results['waiting'] > 0:
            new_status = 'waiting'
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
