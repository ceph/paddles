import logging
from pecan.core import RoutingState
from pecan.hooks import TransactionHook
from sqlalchemy.orm import sessionmaker

log = logging.getLogger(__name__)

class SessionHook(TransactionHook):
    def __init__(self, bind):
        self.bind = bind

    @property
    def session_factory(self):
        return sessionmaker(bind=self.bind, expire_on_commit=False)

    def on_route(self, state):
        # log.info(f"on_route {state.arguments=} {state.request=} {state.response=}")
        state.request.session = self.session_factory()

    def after(self, state: RoutingState):
        # log.info(f"{state.arguments=} {state.request=} {state.response=}")
        session = getattr(state.request, 'session', None)
        status_code = getattr(state.response, 'status_int', 200)
        if session:
            try:
                if status_code > 400:
                    session.rollback()
                else:
                    session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()

    def on_error(self, state: RoutingState, e):
        super().on_error(state, e)
        # log.error(f"{e=} {state.arguments=} {state.request=} {state.response=}")
        session = getattr(state.request, 'session', None)
        if session:
            try:
                session.rollback()
            finally:
                session.close()

    def start(self):
        pass

    def start_ro(self):
        pass

    def commit(self):
        pass

    def rollback(self):
        pass

    def clear(self):
        pass
