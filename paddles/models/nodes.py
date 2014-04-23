from sqlalchemy.orm.exc import DetachedInstanceError
from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer, String,
                        Text)
from sqlalchemy.orm import relationship, backref

from paddles.models import Base


class Node(Base):

    __tablename__ = 'nodes'

    id = Column(Integer, primary_key=True)
    name = Column(String(256), nullable=False, unique=True)
    description = Column(Text)
    up = Column(Boolean(), index=True)

    machine_type = Column(String(32), index=True)
    arch = Column(String(16))
    is_vm = Column(Boolean(), nullable=False, default=False)

    distro = Column(String(32))
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
        'distro',
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

    def __init__(self, name, machine_type=None, arch=None, distro=None,
                 up=None, is_vm=False, vm_host=None, description=None,
                 mac_address=None, ssh_pub_key=None):
        self.name = name
        self.machine_type = machine_type
        self.arch = arch
        self.distro = distro
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
        for k, v in values.items():
            if k in self.allowed_update_keys:
                if k == 'vm_host':
                    vm_host_name = v
                    query = self.query.filter(Node.name == vm_host_name)
                    v = query.one()
                setattr(self, k, v)

    def __json__(self):
        return dict(
            name=self.name,
            description=self.description,
            up=self.up,
            machine_type=self.machine_type,
            is_vm=self.is_vm,
            vm_host=self.vm_host,
            distro=self.distro,
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
