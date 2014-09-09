from webtest import TestApp
from six import b as b_
from pecan import make_app, expose
from pecan.tests.test_hooks import TestTransactionHook
from paddles.decorators import isolation_level
from paddles.hooks import IsolatedTransactionHook


class TestIsolatedTransactionHook(TestTransactionHook):
    def test_isolation_level(self):
        run_hook = []

        class RootController(object):
            @expose(generic=True)
            def index(self):
                run_hook.append('inside')
                return 'I should not be isolated'

            @isolation_level('SERIALIZABLE')
            @index.when(method='POST')
            def isolated(self):
                run_hook.append('inside')
                return "I should be isolated"

        def gen(event):
            return lambda: run_hook.append(event)

        def gen_start(event):
            return lambda level: run_hook.append(' '.join((event, level)))

        def start(isolation_level=''):
            run_hook.append('start ' + isolation_level)

        app = TestApp(make_app(RootController(), hooks=[
            IsolatedTransactionHook(
                start=start,
                start_ro=gen('start_ro'),
                commit=gen('commit'),
                rollback=gen('rollback'),
                clear=gen('clear')
            )
        ]))

        run_hook = []
        response = app.get('/')
        assert response.status_int == 200
        assert response.body == b_('I should not be isolated')

        assert len(run_hook) == 3
        assert run_hook[0] == 'start_ro'
        assert run_hook[1] == 'inside'
        assert run_hook[2] == 'clear'

        run_hook = []
        response = app.post('/')
        assert response.status_int == 200
        assert response.body == b_('I should be isolated')

        assert len(run_hook) == 5
        assert run_hook[0] == 'start '
        assert run_hook[1] == 'start SERIALIZABLE'
        assert run_hook[2] == 'inside'
        assert run_hook[3] == 'commit'
        assert run_hook[4] == 'clear'
