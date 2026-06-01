from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import StatementError

from paddles.exceptions import ForbiddenRequestError
from paddles.models import Node


class TestNodeModel:
    def test_basic_creation(self, session, name):
        node_query = select(Node).filter_by(name=name)
        assert session.scalars(node_query).one_or_none() is None
        node = Node(name=name)
        session.flush()
        session.add(node)
        assert session.scalars(node_query).one()
        node = session.get(Node, node.id)
        assert node is not None
        assert node.name == name

    def test_basic_deletion(self, session, name):
        new_node = Node(name)
        session.add(new_node)
        session.flush()
        node_query = select(Node).filter_by(name=name)
        assert session.scalars(node_query).one()
        session.delete(new_node)
        session.flush()
        assert session.scalars(node_query).one_or_none() is None

    def test_init(self, session, name):
        mtype = "vps"
        session.add(Node(name=name, machine_type=mtype))
        session.flush()
        assert session.scalars(
            select(Node).where(Node.name == name).where(Node.machine_type == mtype)
        ).one()

    def test_invalid(self, session, name):
        session.add(Node(name=name, is_vm="invalid"))
        with pytest.raises(StatementError):
            session.flush()

    def test_vm_host(self, session, name):
        vm_host_name = f"{name}_vm_host"
        vm_guest_names = [f"{name}_vm_guest_1", f"{name}_vm_guest_2"]
        host_node = Node(name=vm_host_name)
        session.add(host_node)
        guest_nodes = []
        for name in vm_guest_names:
            node = Node(name=name)
            session.add(node)
            node.vm_host = host_node
            guest_nodes.append(node)
        session.flush()
        assert len(
            session.scalars(select(Node).where(Node.vm_host == host_node)).all()
        ) == len(vm_guest_names)

        # Test that the backref 'vm_guests' works as well
        query = select(Node)
        for guest in guest_nodes:
            query = query.filter(Node.vm_guests.contains(guest))
        assert host_node == session.scalars(query).one()

    def test_locked_since_locked(self, name):
        user = "cat@door"
        node = Node(name=name)
        node.update(dict(locked=True, locked_by=user))
        # This used to take <100us; since we started flushing on node updates,
        # it takes around 2-3ms.
        assert node.locked_since is not None
        assert (datetime.now(timezone.utc) - node.locked_since) < timedelta(
            milliseconds=5
        )

    def test_locked_since_unlocked(self, name):
        user = "cat@door"
        old_locked_since = datetime(2000, 1, 1, 0, 0)
        node = Node(name=name)
        node.update(dict(locked=True, locked_by=user))
        node.locked_since = old_locked_since
        node.update(dict(locked=False, locked_by=user))
        assert node.locked_since is None

    def test_double_lock(self, name):
        user = "fish@bowl"
        node = Node(name=name)
        node.update(dict(locked=True, locked_by=user))
        with pytest.raises(ForbiddenRequestError):
            node.update(dict(locked=True, locked_by=user))
