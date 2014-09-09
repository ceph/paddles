import pecan.hooks
from pecan.util import _cfg


class IsolatedTransactionHook(pecan.hooks.TransactionHook):
    def get_isolation_level(self, state):
        controller = getattr(state, 'controller', None)
        if controller:
            isolation_level = _cfg(controller).get('isolation_level', None)
        return isolation_level

    def before(self, state):
        if self.is_transactional(state):
            if not getattr(state.request, 'transactional', False):
                self.clear()
                state.request.transactional = True
            isolation_level = self.get_isolation_level(state)
            if isolation_level:
                self.start(isolation_level=isolation_level)
