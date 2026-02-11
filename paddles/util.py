import datetime

import pytz
import tzlocal

localtz = tzlocal.get_localzone()


def local_datetime_to_utc(local_dt) -> datetime.datetime:
    """
    Given a datetime object in the local timezone, convert it to UTC.
    """
    local_dt_aware = localtz.localize(local_dt)
    utc_dt_aware = local_dt_aware.astimezone(pytz.utc)
    utc_dt_naive = utc_dt_aware.replace(tzinfo=None)
    return utc_dt_naive


def coerce_bool(value) -> bool | None:
    if value is None:
        return value
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ["1", "true", "yes"]
    try:
        return int(value) > 0
    except Exception:
        return False
