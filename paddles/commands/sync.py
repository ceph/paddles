from pecan.commands.base import BaseCommand
from datetime import datetime
from paddles.util import local_datetime_to_utc
from paddles.models import start, rollback, commit, Node, Run, Jobs
import requests


def out(string):
    print "==> %s" % string


class SyncCommand(BaseCommand):

    arguments = BaseCommand.arguments + (
        dict(
            name="server",
            help="Import from server",
        ),
    )

    def run(self, args):
        super(SyncCommand, self).run(args)
        self.sync(args, table=Node, get='/nodes/')
        self.sync(args, table=Run, get='/runs/')
        self.sync(args, table=Job, get='/jobs/')
        self.load_app()

    def sync(self, args, table):
        # TODO: load the most recent sync time and add 'get?since=time'
        # otherwise it will reload everything every time
        response = requests.get(args.server + get)
        entries = response.json()
        print "Found {count} {table} to import".format(
            count=len(nodes_json),
            table=table.__class__.__name__)
        out("LOADING ENVIRONMENT")
        try:
            out("STARTING A TRANSACTION...")
            start()
            count = len(entries)
            for i in range(count):
                verb = self.update_entry(table, entries[i])
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

    def update_entry(self, table, entry):
        query = table.query.filter(table.id == entry['id'])
        if query.count():
            node = query.one()
            node.update(entry)
            verb = "Updated"
        else:
            node = table(entry)
            verb = "Created"
        return verb
