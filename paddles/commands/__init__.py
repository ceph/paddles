from pecan import conf
from pecan.commands.base import BaseCommand

from paddles import db


class SessionCommand(BaseCommand):
    """
    A pecan command that talks to the database through a plain SQLAlchemy
    session (there is no request, so no SessionHook).

    Subclasses call ``self.load_app()`` via ``super().run(args)`` and then
    use ``self.session``.
    """

    def run(self, args):
        super().run(args)
        self.load_app()
        self.engine = db.get_engine(conf.sqlalchemy.url)
        self.session = db.get_session(self.engine)

    def commit(self, out=print):
        try:
            self.session.commit()
        except Exception:
            out("Rolling back")
            self.session.rollback()
            raise
