## 2.x
import logging
from datetime import datetime, timezone
from pecan import request
from typing import TYPE_CHECKING, List, Optional

# pre 2.x
import sqlalchemy.exc
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    select,
    # update,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)
from sqlalchemy.orm.exc import DetachedInstanceError

from paddles.decorators import retryOperation
from paddles.exceptions import (
    ForbiddenRequestError,
    InvalidRequestError,
    ResourceUnavailableError,
)
from paddles.models import Base

from .job_nodes import job_nodes_table

if TYPE_CHECKING:
    from paddles.models import Job

log = logging.getLogger(__name__)


class Node(Base):
    __tablename__ = "nodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(
        String(256), nullable=False, unique=True, index=True
    )
    description: Mapped[str] = mapped_column(nullable=True)
    up: Mapped[bool] = mapped_column(
        Boolean(), nullable=False, default=False, index=True
    )

    machine_type: Mapped[str] = mapped_column(String(32), index=True)
    arch: Mapped[str] = mapped_column(String(16), nullable=True)
    is_vm: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)

    os_type: Mapped[str] = mapped_column(String(32), nullable=True)
    os_version: Mapped[str] = mapped_column(String(16), index=True, nullable=True)
    vm_host: Mapped[Optional["Node"]] = relationship(
        "Node",
        back_populates="vm_guests",
        remote_side="Node.id",
        order_by="Node.name",
    )
    vm_host_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("nodes.id"))
    vm_guests: Mapped[List["Node"]] = relationship("Node")

    jobs: Mapped[List["Job"]] = relationship(
        "Job",
        secondary=job_nodes_table,
        lazy="dynamic",
    )

    locked: Mapped[bool] = mapped_column(
        Boolean(), nullable=False, default=False, index=True
    )
    locked_by: Mapped[Optional[str]] = mapped_column(
        String(64), index=True, nullable=True
    )
    locked_since: Mapped[Optional[datetime]] = mapped_column(DateTime)

    mac_address: Mapped[str] = mapped_column(String(17), nullable=True)
    ssh_pub_key: Mapped[str] = mapped_column(Text, nullable=True)

    allowed_update_keys = [
        "arch",
        "description",
        "os_type",
        "os_version",
        "is_vm",
        "locked",
        "locked_by",
        "locked_since",
        "mac_address",
        "machine_type",
        "ssh_pub_key",
        "up",
        "vm_host",
    ]

    def __init__(
        self,
        name,
        machine_type="",
        arch="",
        os_type="",
        os_version="",
        up=False,
        is_vm=False,
        vm_host=None,
        description="",
        mac_address="",
        ssh_pub_key=None,
    ):
        self.name = name
        self.machine_type = machine_type
        self.arch = arch
        self.os_type = os_type
        self.os_version = os_version
        self.up = up
        self.is_vm = is_vm
        self.vm_host = vm_host
        self.description = description
        self.mac_address = mac_address
        self.ssh_pub_key = ssh_pub_key

    @retryOperation(
        attempts=20,
        exceptions=(
            sqlalchemy.exc.InvalidRequestError,
            sqlalchemy.exc.OperationalError,
        ),
    )
    def update(self, values):
        """
        :param values: a dict.
        """
        self._check_for_update(values)
        was_locked = self.locked

        for k, v in values.items():
            if k in self.allowed_update_keys:
                # if k == "vm_host":
                #     vm_host_name = v
                #     v = self.session.scalars(
                #         select(Node).where(Node.name == vm_host_name)
                #     ).one()
                setattr(self, k, v)

        if "locked" in values:
            if self.locked != was_locked:
                self.locked_since = datetime.now(timezone.utc) if self.locked else None
            if not self.locked:
                self.locked_by = None
        # self.session.flush()

    def _check_for_update(self, values):
        """
        If the given values are safe, do nothing. If not, raise the appropriate
        exception.
        """
        locking = values.get("locked")
        if locking not in (True, False):
            return
        was_locked = self.locked
        if was_locked is None:
            return
        desc = values.get("description")
        to_lock_for = values.get("locked_by")
        verb = {False: "unlock", True: "lock"}.get(locking)
        if was_locked == locking:
            if (
                self.locked_by != to_lock_for
                or desc is None
                or desc != self.description
            ):
                raise ForbiddenRequestError(
                    "Cannot {verb} an already-{verb}ed node".format(verb=verb)
                )
        elif not to_lock_for:
            raise InvalidRequestError(
                "Cannot {verb} without specifying locked_by".format(verb=verb)
            )
        elif verb == "unlock" and was_locked and to_lock_for != self.locked_by:
            raise ForbiddenRequestError(
                "Cannot {verb} - locked_by values must match".format(verb=verb)
            )
        elif verb == "unlock" and was_locked and desc and desc != self.description:
            raise ForbiddenRequestError(
                "Cannot {verb} - description values must match".format(verb=verb)
            )

    @classmethod
    def lock_many(
        cls,
        count,
        locked_by,
        machine_type,
        description=None,
        os_type=None,
        os_version=None,
        arch=None,
    ):
        session = request.session
        update_dict = dict(
            locked=True,
            locked_by=locked_by,
            locked_since=datetime.now(timezone.utc),
            description=description,
        )

        query = select(Node)
        if "|" in machine_type:
            machine_types = machine_type.split("|")
            query = query.filter(Node.machine_type.in_(machine_types))
        else:
            query = query.filter(Node.machine_type == machine_type)
        if os_type:
            query = query.filter(Node.os_type == os_type)
        if os_version:
            query = query.filter(Node.os_version == os_version)
        if arch:
            query = query.filter(Node.arch == arch)

        query = query.filter(Node.up.is_(True))
        query = query.filter(Node.locked.is_(False))
        query = query.order_by(Node.id)
        query = query.limit(count)
        query = query.with_for_update()
        nodes = [n for n in session.execute(query).scalars().all()]
        log.info(f"before update: {nodes=}")
        if (nodes_avail := len(nodes)) < count:
            raise ResourceUnavailableError(
                "only {count} nodes available".format(count=nodes_avail)
            )
        for node in nodes:
            node.update(update_dict)
        log.info(f"after update: {nodes=}")
        log.info(f"locked {nodes=}")
        return nodes

    def __json__(self):
        return dict(
            name=self.name,
            description=self.description,
            up=self.up,
            machine_type=self.machine_type,
            is_vm=self.is_vm,
            vm_host=self.vm_host,
            os_type=self.os_type,
            os_version=self.os_version,
            arch=self.arch,
            locked=self.locked,
            locked_since=self.locked_since,
            locked_by=self.locked_by,
            mac_address=self.mac_address,
            ssh_pub_key=self.ssh_pub_key,
        )

    def __repr__(self):
        try:
            return "<Node %s>" % self.name
        except DetachedInstanceError:
            return "<Node detached>"
