from pecan.commands.base import BaseCommand
from datetime import datetime
from paddles.util import local_datetime_to_utc
from paddles.models import start, rollback, commit, Node
import requests


def out(string):
    print "==> %s" % string


class ImportNodesCommand(BaseCommand):
    """
    Import Node information from a teuthology lock server
    """

    lockserver = 'http://teuthology.front.sepia.ceph.com/locker/lock'

    def run(self, args):
        super(ImportNodesCommand, self).run(args)
        response = requests.get(self.lockserver)
        nodes_json = response.json()
        print "Found {count} nodes to import".format(count=len(nodes_json))
        out("LOADING ENVIRONMENT")
        self.load_app()
        try:
            out("STARTING A TRANSACTION...")
            start()
            self.vm_hosts = {}
            count = len(nodes_json)
            for i in range(count):
                node_json = nodes_json[i]
                verb = self.update_node(node_json)
                print "{verb} {n}/{count}\r".format(verb=verb, n=i+1,
                                                    count=count),
            print
        except:
            rollback()
            out("ROLLING BACK... ")
            raise
        else:
            out("COMMITING... ")
            commit()

    def update_node(self, node_json):
        name = node_json['name'].split('@')[1]
        query = Node.query.filter(Node.name == name)
        if query.count():
            node = query.one()
            verb = "Updated"
        else:
            node = Node(name)
            verb = "Created"

        vm_host_name = node_json.get('vpshost', '')
        is_vm = vm_host_name not in (None, '')
        if is_vm:
            self.vm_hosts[name] = node_json['vpshost']

        locked_since_local = datetime.strptime(node_json['locked_since'],
                                               '%Y-%m-%dT%H:%M:%S')
        locked_since = local_datetime_to_utc(locked_since_local)

        node.machine_type = node_json.get('type')
        node.arch = node_json.get('arch')
        node.distro = node_json.get('distro')
        node.up = node_json.get('up', 0) == 1
        node.is_vm = is_vm
        node.mac_address = node_json.get('mac').lower()
        node.ssh_pub_key = node_json.get('sshpubkey')
        node.locked = node_json.get('locked') == 1
        node.locked_by = node_json.get('locked_by')
        node.locked_since = locked_since
        node.description = node_json.get('description')

        return verb

    def set_vm_hosts(self):
        print "Setting VM hosts..."
        vms = Node.query.filter(Node.is_vm.is_(True))
        for vm in vms:
            host_name = self.vm_hosts[vm.name]
            if not host_name:
                continue
            vm_host = Node.query.filter(Node.name.like(host_name + '%')).one()
            vm.vm_host = vm_host
