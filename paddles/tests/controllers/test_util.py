from paddles.controllers.util import ReadableSeconds


class TestReadableSeconds(object):
    def test_second(self):
        rs = ReadableSeconds(1)
        assert str(rs) == '1 second'

    def test_minute(self):
        rs = ReadableSeconds(1 * 60)
        assert str(rs) == '1 minute'

    def test_hour(self):
        rs = ReadableSeconds(1 * 60 * 60)
        assert str(rs) == '1 hour'

    def test_day(self):
        rs = ReadableSeconds(1 * 60 * 60 * 24)
        assert str(rs) == '1 day'

    def test_month(self):
        rs = ReadableSeconds(1 * 60 * 60 * 24 * 31)
        assert str(rs) == '1 month'

    def test_year(self):
        rs = ReadableSeconds(1 * 60 * 60 * 24 * 31 * 12)
        assert str(rs).startswith('1 year')

    def test_all(self):
        rs = ReadableSeconds(
            1 + 60 + 60*60 + 60*60*24 + 60*60*24*31 + 60*60*24*365
        )
        assert str(rs) == '1 year, 1 month, 1 day, 1 hour, 1 minute, 1 second'
