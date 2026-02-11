from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import StatementError

from paddles import models
from paddles.exceptions import ForbiddenRequestError
from paddles.models import Node, Session
from paddles.tests import TestModel


class TestNodeModel(TestModel):
    def test_basic_creation(self):
        name = "new_node"
        node_query = select(Node).filter_by(name=name)
        assert Session.scalars(node_query).one_or_none() is None
        node = Node(name=name)
        models.commit()
        Session.add(node)
        assert Session.scalars(node_query).one()
        node = Session.get(Node, 1)
        assert node is not None
        assert node.name == name

    def test_basic_deletion(self):
        name = "test_basic_deletion"
        new_node = Node(name)
        Session.add(new_node)
        models.commit()
        node_query = select(Node).filter_by(name=name)
        assert Session.scalars(node_query).one()
        Session.delete(new_node)
        models.commit()
        assert Session.scalars(node_query).one_or_none() is None

    def test_init(self):
        name = "test_init"
        mtype = "vps"
        Session.add(Node(name=name, machine_type=mtype))
        models.commit()
        assert Session.scalars(
            select(Node).where(Node.name == name).where(Node.machine_type == mtype)
        ).one()

    def test_invalid(self):
        name = "test_invalid"
        Session.add(Node(name=name, is_vm="invalid"))
        with pytest.raises(StatementError):
            models.commit()

    def test_vm_host(self):
        vm_host_name = "vm_host"
        vm_guest_names = ["vm_guest_1", "vm_guest_2"]
        host_node = Node(name=vm_host_name)
        Session.add(host_node)
        guest_nodes = []
        for name in vm_guest_names:
            node = Node(name=name)
            Session.add(node)
            node.vm_host = host_node
            guest_nodes.append(node)
        models.commit()
        assert len(
            Session.scalars(select(Node).where(Node.vm_host == host_node)).all()
        ) == len(vm_guest_names)

        # Test that the backref 'vm_guests' works as well
        query = select(Node)
        for guest in guest_nodes:
            query = query.filter(Node.vm_guests.contains(guest))
        assert host_node == Session.scalars(query).one()

    def test_locked_since_locked(self):
        node_name = "cats"
        user = "cat@door"
        node = Node(name=node_name)
        node.update(dict(locked=True, locked_by=user))
        # This used to take <100us; since we started flushing on node updates,
        # it takes around 2-3ms.
        assert node.locked_since is not None
        assert (datetime.now(timezone.utc) - node.locked_since) < timedelta(
            milliseconds=5
        )

    def test_locked_since_unlocked(self):
        node_name = "cats"
        user = "cat@door"
        old_locked_since = datetime(2000, 1, 1, 0, 0)
        node = Node(name=node_name)
        node.update(dict(locked=True, locked_by=user))
        node.locked_since = old_locked_since
        node.update(dict(locked=False, locked_by=user))
        assert node.locked_since is None

    def test_double_lock(self):
        node_name = "goldfish"
        user = "fish@bowl"
        node = Node(name=node_name)
        node.update(dict(locked=True, locked_by=user))
        with pytest.raises(ForbiddenRequestError):
            node.update(dict(locked=True, locked_by=user))
