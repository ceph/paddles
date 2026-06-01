from pecan import configuration
from pecan.commands.base import BaseCommand

from paddles import db, models


def out(string):
    print("==> %s" % string)


class PopulateCommand(BaseCommand):
    """
    Load a pecan environment and initializate the database.
    """

    def run(self, args):
        super(PopulateCommand, self).run(args)
        config = configuration.conf_from_file(args.config_file).to_dict()
        engine = db.get_engine(config["sqlalchemy"]["url"])
        session = db.get_session(engine)
        out("LOADING ENVIRONMENT")
        self.load_app()
        out("BUILDING SCHEMA")
        try:
            out("STARTING A TRANSACTION...")
            models.Base.metadata.create_all(engine)
        except:
            session.rollback()
            out("ROLLING BACK... ")
            raise
        else:
            out("COMMITING... ")
            session.commit()
