import sqlalchemy.exc
from sqlalchemy.orm.exc import DetachedInstanceError
from sqlalchemy.sql import text
from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer, String,
                        Text)
from sqlalchemy.orm import relationship, backref
from datetime import datetime

from paddles.exceptions import (InvalidRequestError, ForbiddenRequestError,
                                RaceConditionError, ResourceUnavailableError)
from paddles.models import Base, commit, rollback

import logging
log = logging.getLogger(__name__)


class Node(Base):

    __tablename__ = 'nodes'

    id = Column(Integer, primary_key=True)
    name = Column(String(256), nullable=False, unique=True, index=True)
    description = Column(Text)
    up = Column(Boolean(), index=True)

    machine_type = Column(String(32), index=True)
    arch = Column(String(16))
    is_vm = Column(Boolean(), nullable=False, default=False)

    os_type = Column(String(32))
    os_version = Column(String(16), index=True)
    vm_host = relationship("Node",
                           backref=backref('vm_guests'),
                           remote_side='Node.id',
                           order_by='Node.name',
                           )
    vm_host_id = Column(Integer, ForeignKey('nodes.id'))

    locked = Column(Boolean(), nullable=False, default=False, index=True)
    locked_by = Column(String(64), index=True)
    locked_since = Column(DateTime)

    mac_address = Column(String(17))
    ssh_pub_key = Column(Text)

    allowed_update_keys = [
        'arch',
        'description',
        'os_type',
        'os_version',
        'is_vm',
        'locked',
        'locked_by',
        'locked_since',
        'mac_address',
        'machine_type',
        'ssh_pub_key',
        'up',
        'vm_host',
    ]

    def __init__(self, name, machine_type=None, arch=None, os_type=None,
                 os_version=None, up=None, is_vm=False, vm_host=None,
                 description=None, mac_address=None, ssh_pub_key=None):
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

    def update(self, values):
        """
        :param values: a dict.
        """
        self._check_for_update(values)
        was_locked = self.locked

        for k, v in values.items():
            if k in self.allowed_update_keys:
                if k == 'vm_host':
                    vm_host_name = v
                    query = self.query.filter(Node.name == vm_host_name)
                    v = query.one()
                setattr(self, k, v)

        if 'locked' in values:
            if self.locked != was_locked:
                self.locked_since = datetime.utcnow() if self.locked else None
            if not self.locked:
                self.locked_by = None

    def _check_for_update(self, values):
        """
        If the given values are safe, do nothing. If not, raise the appropriate
        exception.
        """
        locking = values.get('locked')
        was_locked = self.locked
        desc = values.get('description')
        if locking in (True, False) and was_locked is not None:
            to_lock_for = values.get('locked_by')
            verb = {False: 'unlock', True: 'lock'}.get(locking)
            if was_locked == locking:
                if (self.locked_by != to_lock_for or desc is None or desc !=
                        self.description):
                    raise ForbiddenRequestError(
                        "Cannot {verb} an already-{verb}ed node".format(
                            verb=verb))
            elif not to_lock_for:
                raise InvalidRequestError(
                    "Cannot {verb} without specifying locked_by".format(
                        verb=verb))
            elif (verb == 'unlock' and was_locked and to_lock_for !=
                  self.locked_by):
                raise ForbiddenRequestError(
                    "Cannot {verb} - locked_by values must match".format(
                        verb=verb))
            elif (verb == 'unlock' and was_locked and desc and desc !=
                  self.description):
                raise ForbiddenRequestError(
                    "Cannot {verb} - description values must match".format(
                        verb=verb))

    @classmethod
    def find(cls, count=None, locked=None, locked_by=None, machine_type=None,
             description=None, os_type=None, os_version=None, arch=None,
             up=None):
        query = cls.query
        if machine_type:
            if '|' in machine_type:
                machine_types = machine_type.split('|')
                query = query.filter(Node.machine_type.in_(machine_types))
            else:
                query = query.filter(Node.machine_type == machine_type)
        if os_type:
            query = query.filter(Node.os_type == os_type)
        if os_version:
            query = query.filter(Node.os_version == os_version)
        if arch:
            query = query.filter(Node.arch == arch)
        if up is not None:
            query = query.filter(Node.up == up)
        if locked is not None:
            query = query.filter(Node.locked == locked)
        if locked_by:
            query = query.filter(Node.locked_by == locked_by)
        if count:
            query = query.limit(count)
        return query

    @classmethod
    def lock_many(cls, count, locked_by, machine_type, description=None,
                  os_type=None, os_version=None, arch=None):
        query = cls.find(
            locked=False,
            up=True,
            count=count,
            machine_type=machine_type,
            os_type=os_type,
            os_version=os_version,
            arch=arch,
        )

        nodes = query.all()
        nodes_avail = len(nodes)
        if nodes_avail < count:
            raise ResourceUnavailableError(
                "only {count} nodes available".format(count=nodes_avail))

        update_dict = dict(
            locked=True,
            locked_by=locked_by,
            description=description,
        )

        for node in nodes:
            node.update(update_dict)
        try:
            commit()
        except (sqlalchemy.exc.DBAPIError, sqlalchemy.exc.InvalidRequestError):
            rollback()
            raise RaceConditionError(
                "error locking nodes. please retry request."
            )
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
            return '<Node %s>' % self.name
        except DetachedInstanceError:
            return '<Node detached>'
