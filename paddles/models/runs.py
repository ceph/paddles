import re
from datetime import datetime, timezone
from typing import List

from sqlalchemy import (
    DateTime,
    Integer,
    SQLColumnExpression,
    String,
    case,
    func,
    select,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)
from sqlalchemy.orm.exc import DetachedInstanceError

from paddles import conf
from paddles.models import TEUTHOLOGY_TIMESTAMP_FMT, Base, Session
from paddles.models.jobs import Job
from paddles.util import local_datetime_to_utc

suite_names = [
    "big",
    "ceph-deploy",
    "clusters",
    "dummy",
    "experimental",
    "fs",
    "hadoop",
    "iozone",
    "kcephfs",
    "knfs",
    "krbd",
    "marginal",
    "mixed-clients",
    "mount",
    "multimds",
    "nfs",
    "powercycle",
    "rados",
    "rbd",
    "rest",
    "rgw",
    "samba",
    "smoke",
    "stress",
    "tgt",
    "upgrade:dumpling-x:stress-split",
    "upgrade:dumpling-x",
    "upgrade:dumpling-emperor-x",
    "upgrade-cuttlefish",
    "upgrade-dumpling",
    "upgrade-fs",
    "upgrade-mixed-cluster",
    "upgrade-mixed-mons",
    "upgrade-parallel",
    "upgrade-rados-double",
    "upgrade-rados",
    "upgrade-rbd-double",
    "upgrade-rbd",
    "upgrade-rgw-double",
    "upgrade-rgw",
    "upgrade-small",
    "upgrade",
    "workload",
]


machine_types = ["burnupi", "mira", "plana", "saya", "tala", "vps"]


distros = ["centos", "debian", "fedora", "opensuse", "rhel", "suse", "ubuntu"]


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
    regex_templ_base = "(?P<user>.*)-(?P<scheduled>{time})-(?P<suite>{suites})-(?P<branch>.+)-(?P<kernel_branch>.+)-(?P<flavor>[^-]+)"  # noqa
    regex_templ_mtype = regex_templ_base + "-(?P<machine_type>{mtypes})".format(
        mtypes="|".join(machine_types)
    )
    regex_templ_distro = regex_templ_mtype + "-(?P<distro>({distros}))".format(
        distros="|".join(distros)
    )

    # Append '[^-]*' to each suite name to handle suite slices like
    # 'rados:thrash'
    modded_names = [name + "[^-]*" for name in suite_names]
    suites_str = "({names_str})".format(names_str="|".join(modded_names))
    return [
        templ.format(time=timestamp_regex, suites=suites_str)
        for templ in (
            regex_templ_distro + "$",
            regex_templ_mtype + "$",
            regex_templ_base + "$",
        )
    ]


class Run(Base):
    timestamp_regex = (
        "[0-9]{1,4}-[0-9]{1,2}-[0-9]{1,2}_[0-9]{1,2}:[0-9]{1,2}:[0-9]{1,2}"
    )
    name_regexes = get_name_regexes(
        timestamp_regex, suite_names, distros, machine_types
    )
    backup_name_regex = (
        "(?P<user>.*)-(?P<scheduled>%s)-(?P<suite>.*)-(?P<branch>.*)-.*?-.*?-(?P<machine_type>.*?)"
        % timestamp_regex
    )  # noqa

    __tablename__ = "runs"
    id = mapped_column(Integer, primary_key=True)
    name = mapped_column(String(512), index=True, unique=True)
    status_ = mapped_column(String(16), index=True, name="status")
    user = mapped_column(String(32), index=True)
    scheduled = mapped_column(DateTime, index=True)
    suite = mapped_column(String(256), index=True)
    branch = mapped_column(String(128), index=True)
    machine_type = mapped_column(String(32), index=True)
    posted = mapped_column(DateTime, index=True)
    started = mapped_column(DateTime, index=True)
    updated = mapped_column(DateTime, index=True)
    jobs: Mapped[List["Job"]] = relationship(
        "Job",
        back_populates="run",
        cascade="all,delete",
        order_by="Job.job_id",
        lazy="dynamic",
    )

    allowed_statuses = (
        "empty",
        "queued",
        "running",
        "waiting",
        "unknown",
        "finished pass",
        "finished dead",
        "finished fail",
    )

    def __init__(self, name):
        self.name = name
        self.posted = datetime.now(timezone.utc)
        parsed_name = self.parse_name()
        self.user = parsed_name.get("user", "")
        if "scheduled" in parsed_name:
            scheduled_local = parsed_name["scheduled"]
            self.scheduled = local_datetime_to_utc(scheduled_local)
        else:
            self.scheduled = self.posted
        self.suite = parsed_name.get("suite", "")
        self.branch = parsed_name.get("branch", "")
        self.machine_type = parsed_name.get("machine_type", "")

    def __repr__(self):
        try:
            return "<Run %r>" % self.name
        except DetachedInstanceError:
            return "<Run detached>"

    def __json__(self):
        results = self.results
        return dict(
            name=self.name,
            href=self.href,
            user=self.user,
            results=results,
            status=self.status,
            jobs_count=results["total"],
            posted=self.posted,
            scheduled=self.scheduled,
            started=self.started,
            updated=self.updated,
            branch=self.branch,
            suite=self.suite,
            machine_type=self.machine_type,
            sha1=results["sha1"],
            priority=self.priority,
            flavor=results["flavor"],
        )

    @classmethod
    def _parse_name(cls, name):
        name_match = (
            re.match(cls.name_regexes[0], name)
            or re.match(cls.name_regexes[1], name)
            or re.match(cls.name_regexes[2], name)
            or re.match(cls.backup_name_regex, name)
        )
        if name_match:
            match_dict = name_match.groupdict()
            for key, value in match_dict.items():
                match_dict[key] = value.strip(" -")

            match_dict["scheduled"] = datetime.strptime(
                match_dict["scheduled"], TEUTHOLOGY_TIMESTAMP_FMT
            )
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
        if self.jobs:
            return sorted([job.updated for job in self.jobs])[-1]
        else:
            return max(self.scheduled, self.posted)

    @property
    def href(self):
        return ("%s/runs/%s/" % (conf["address"], self.name),)

    @property
    def priority(self):
        jobs = self.jobs
        if jobs:
            job = jobs[0]
            return job.priority

    @hybrid_property
    def total_jobs(self):
        with Session.no_autoflush:
            return len(self.jobs)

    @total_jobs.inplace.expression
    def _total_jobs_expr(cls):
        return select(func.count(1)).where(Job.run_id == cls.id).label("total_jobs")

    @hybrid_property
    def results(self):
        result = {key: 0 for key in Job.allowed_statuses}
        for job in self.jobs:
            result[job.status] = result.get(job.status, 0) + 1
        result["total"] = len(self.jobs)
        result["sha1"] = self.jobs[0].sha1 if self.jobs else None
        result["flavor"] = self.jobs[0].flavor if self.jobs else None
        return result

    @results.inplace.expression
    def _results_expr(cls):
        return (
            select(Job.status, func.count())
            .where(Job.run_id == cls.id)
            .group_by(Job.status)
            .scalar_subquery()
        )

    @hybrid_property
    def status(self):
        if self.total_jobs == 0:
            return "empty"
        results = self.results
        total = results["total"]

        if results["queued"] == total:
            new_status = "queued"
        elif results["running"] > 0:
            new_status = "running"
        elif results["waiting"] > 0:
            new_status = "waiting"
        elif results["dead"] == total:
            new_status = "finished dead"
        elif results["fail"] > 0:
            new_status = "finished fail"
        elif results["dead"] > 0:
            new_status = "finished fail"
        elif results["pass"] == total:
            new_status = "finished pass"
        elif results["queued"]:
            new_status = "queued"
        else:
            new_status = "unknown"
        return new_status

    @status.inplace.expression
    def _status_expr(cls) -> SQLColumnExpression[String]:
        def count_status(status):
            return (
                select(func.count(1))
                .select_from(Job)
                .where(Job.run_id == cls.id)
                .where(Job.status == "running")
                .scalar_subquery()
            )

        stmt = case(
            (cls.total_jobs == 0, "empty"),
            (count_status("queued") == cls.total_jobs, "queued"),
            (count_status("running") > 0, "running"),
            (count_status("waiting") > 0, "waiting"),
            (count_status("dead") == cls.total_jobs, "finished dead"),
            (count_status("fail") > 0, "finished fail"),
            (count_status("dead") > 0, "finished fail"),
            (count_status("pass") == cls.total_jobs, "finished pass"),
            (count_status("queued") > 0, "queued"),
            else_="unknown",
        )
        return stmt
