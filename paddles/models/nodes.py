from sqlalchemy import (Boolean, Column, DateTime, Enum, ForeignKey, Integer,
                        String, Text)
from sqlalchemy.orm import relationship, backref

from paddles.models import Base


machine_types = ('plana', 'mira', 'vps', 'burnupi', 'tala', 'saya', 'dubia')


class Node(Base):

    __tablename__ = 'nodes'

    id = Column(Integer, primary_key=True)
    name = Column(String(256), nullable=False)
    description = Column(Text)
    up = Column(Boolean(), nullable=False, index=True)

    machine_type = Column(Enum(*machine_types, name="machine_type"),
                          nullable=False, index=True)
    arch = Column(String(16), nullable=False, index=True)
    is_vm = Column(Boolean(), nullable=False, default=False)

    distro = Column(String(32), index=True)
    vm_host = relationship("Node",
                           backref=backref('vm_guests'),
                           remote_side='Node.id',
                           order_by='Node.name',
                           )
    vm_host_id = Column(Integer, ForeignKey('nodes.id'))

    locked = Column(Boolean(), nullable=False, default=False, index=True)
    locked_by = Column(String(64), index=True)
    locked_since = Column(DateTime, index=True)

    mac_address = Column(String(17))
    ssh_pub_key = Column(Text)

    def __init__(self, name, machine_type, arch, distro, up, is_vm=False,
                 vm_host=None, description=None, mac_address=None,
                 ssh_pub_key=None):
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
