from paddles.decorators import retryOperation
from pytest import raises
from mock import Mock


class GoodException(BaseException):
    pass


class BadException(BaseException):
    pass


class TestRetryOperation(object):
    def test_basic(self):
        func = Mock()
        func.return_value = "retried"
        decorated = retryOperation()(func)
        assert decorated() == "retried"
        assert func.call_count == 1

    def test_retried(self):
        func = Mock()
        func.side_effect = [GoodException(), 0]
        decorated = retryOperation(exceptions=[GoodException])(func)
        assert decorated() == 0
        assert func.call_count == 2

    def test_wrong_exception(self):
        func = Mock()
        func.side_effect = [GoodException(), BadException(), True]
        decorated = retryOperation(exceptions=[GoodException])(func)
        with raises(BadException):
            assert decorated() is None
        assert func.call_count == 2

    def test_exhausted(self):
        func = Mock()
        func.side_effect = [GoodException(), GoodException(), True]
        decorated = retryOperation(attempts=2, exceptions=[GoodException])(func)
        with raises(GoodException):
            assert decorated() is None
        assert func.call_count == 2
