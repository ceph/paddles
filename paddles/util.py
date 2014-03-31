import tzlocal
import pytz


localtz = tzlocal.get_localzone()


def local_datetime_to_utc(local_dt):
    """
    Given a datetime object in the local timezone, convert it to UTC.
    """
    local_dt_aware = localtz.localize(local_dt)
    utc_dt_aware = local_dt_aware.astimezone(pytz.utc)
    utc_dt_naive = utc_dt_aware.replace(tzinfo=None)
    return utc_dt_naive
