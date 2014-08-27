from paddles.models import Node
from paddles.tests import TestApp
from paddles import models

from sqlalchemy.exc import StatementError

from datetime import datetime, timedelta

import pytest


class TestNodeModel(TestApp):

    def test_basic_creation(self):
        Node(name='new_node')
        models.commit()
        assert Node.get(1).name == 'new_node'

    def test_basic_deletion(self):
        new_node = Node('test_basic_deletion')
        models.commit()
        new_node.delete()
        models.commit()
        query = Node.query.filter(Node.name == 'test_basic_deletion')
        assert not query.count()

    def test_init(self):
        name = 'test_init'
        mtype = 'vps'
        Node(name=name, machine_type=mtype)
        models.commit()
        query = Node.query.filter(Node.name == name)\
            .filter(Node.machine_type == mtype)
        assert query.one()

    def test_invalid(self):
        name = 'test_invalid'
        Node(name=name, is_vm='invalid')
        with pytest.raises(StatementError):
            models.commit()

    def test_vm_host(self):
        vm_host_name = 'vm_host'
        vm_guest_names = ['vm_guest_1', 'vm_guest_2']
        host_node = Node(name=vm_host_name)
        guest_nodes = []
        for name in vm_guest_names:
            node = Node(name=name)
            node.vm_host = host_node
            guest_nodes.append(node)
        models.commit()
        query = Node.query.filter(Node.vm_host == host_node)
        assert query.count() == len(vm_guest_names)

        # Test that the backref 'vm_guests' works as well. I am intentionally
        # testing two things here.
        query = Node.query
        for guest in guest_nodes:
            query = query.filter(Node.vm_guests.contains(guest))
        assert host_node == query.one()

    def test_locked_since_locked(self):
        node_name = 'cats'
        node = Node(name=node_name)
        node.update(dict(locked=True))
        assert (datetime.utcnow() - node.locked_since) < timedelta(0, 0, 100)

    def test_locked_since_unlocked(self):
        node_name = 'cats'
        old_locked_since = datetime(2000, 1, 1, 0, 0)
        node = Node(name=node_name)
        node.locked = True
        node.locked_since = old_locked_since
        node.update(dict(locked=False))
        assert node.locked_since is None

    def test_double_lock(self):
        node_name = 'goldfish'
        node = Node(name=node_name)
        node.update(dict(locked=True))
        with pytest.raises(RuntimeError):
            node.update(dict(locked=True))
