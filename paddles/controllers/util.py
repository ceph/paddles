from datetime import datetime, timedelta


def offset_query(query, page_size, page):
    count = int(page_size)
    page = int(page)
    if page > 1:
        offset = count * (page - 1)
        if offset > query.count():
            return []
        query = query.offset(offset)
    query = query.limit(count)
    return query


def last_seen(model_obj):
    now = datetime.utcnow()
    try:
        last_obj = model_obj.query[0].posted
        if not last_obj:
            last_obj = now
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
        return "{0}{1}{2}{3}{4}{5}".format(
            self.years,
            self.months,
            self.days,
            self.hours,
            self.minutes,
            self.seconds,
        ).rstrip(' ,')

    @property
    def years(self):
        # Subtract 1 here because the earliest datetime() is 1/1/1
        years = self.relative.year - 1
        year_str = 'years' if years > 1 else 'year'
        if years:
            return "%d %s, " % (years, year_str)
        return ""

    @property
    def months(self):
        # Subtract 1 here because the earliest datetime() is 1/1/1
        months = self.relative.month - 1
        month_str = 'months' if months > 1 else 'month'
        if months:
            return "%d %s, " % (months, month_str)
        return ""

    @property
    def days(self):
        # Subtract 1 here because the earliest datetime() is 1/1/1
        days = self.relative.day - 1
        day_str = 'days' if days > 1 else 'day'
        if days:
            return "%d %s, " % (days, day_str)
        return ""

    @property
    def hours(self):
        hours = self.relative.hour
        hour_str = 'hours' if hours > 1 else 'hour'
        if hours:
            return "%d %s, " % (self.relative.hour, hour_str)
        return ""

    @property
    def minutes(self):
        minutes = self.relative.minute
        minutes_str = 'minutes' if minutes > 1 else 'minute'
        if minutes:
            return "%d %s, " % (self.relative.minute, minutes_str)
        return ""

    @property
    def seconds(self):
        seconds = self.relative.second
        seconds_str = 'seconds' if seconds > 1 else 'second'
        if seconds:
            return "%d %s, " % (self.relative.second, seconds_str)
        return ""

