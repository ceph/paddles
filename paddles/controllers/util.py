from datetime import datetime, timedelta


def last_seen(model_obj):
    now = datetime.utcnow()
    try:
        last_obj = model_obj.query[0].timestamp
    except IndexError:
        last_obj = now
    difference = now - last_obj
    formatted = ReadableSeconds(difference.seconds)
    return "%s ago" % formatted


class ReadableSeconds(object):

    def __init__(self, seconds):
        self.original_seconds = seconds

    @property
    def relative(self):
        """
        Generate a relative datetime object based on current seconds
        """
        return datetime(1, 1, 1) + timedelta(seconds=self.original_seconds)

    def __str__(self):
        return "%s%s%s%s" % (
            self.days,
            self.hours,
            self.minutes,
            self.seconds,
        )

    @property
    def days(self):
        days = self.relative.day
        day_str = 'days' if days > 1 else 'day'
        if days:
            return "%d %s, " % (days, day_str)
        return ""

    @property
    def hours(self):
        hours = self.relative.hour
        hour_str = 'hours' if hours > 1 else 'hour'
        if hours:
            return "%d %s, " % (self.relative.hours, hour_str)
        return ""

    @property
    def minutes(self):
        minutes = self.relative.minute
        minutes_str = 'minutes' if minutes > 1 else 'minute'
        if minutes:
            return "%d %s, " % (self.relative.minutes, minutes_str)
        return ""

    @property
    def seconds(self):
        seconds = self.relative.second
        seconds_str = 'seconds' if seconds > 1 else 'second'
        if seconds:
            return "%d %s, " % (self.relative.seconds, seconds_str)
        return ""

