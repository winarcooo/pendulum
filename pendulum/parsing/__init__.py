import re
import copy

from datetime import datetime, date, time
from dateutil import parser

from .exceptions import ParserError

try:
    from ._iso8601 import parse_iso8601
except ImportError:
    from .iso8601 import parse_iso8601


COMMON = re.compile(
    # Date (optional)
    '^'
    '(?P<date>'
    '    (?P<classic>'  # Classic date (YYYY-MM-DD)
    '        (?P<year>\d{4})'  # Year
    '        (?P<monthday>'
    '            (?P<monthsep>[/:])?(?P<month>\d{2})'  # Month (optional)
    '            ((?P<daysep>[/:])?(?P<day>\d{2}))'  # Day (optional)
    '        )?'
    '    )'
    ')?'

    # Time (optional)
    '(?P<time>'
    '    (?P<timesep>\ )?'  # Separator (space)
    '    (?P<hour>\d{1,2}):(?P<minute>\d{1,2})?:(?P<second>\d{1,2})?'  # HH:mm:ss (optional mm and ss)
    # Subsecond part (optional)
    '    (?P<subsecondsection>'
    '        (?:[.|,])'  # Subsecond separator (optional)
    '        (?P<subsecond>\d{1,9})'  # Subsecond
    '    )?'
    ')?'
    '$',
    re.VERBOSE
)


DEFAULT_OPTIONS = {
    'day_first': False,
    'year_first': True,
    'strict': True,
    'exact': False,
    'now': None
}


def parse(text, **options):
    """
    Parses a string with the given options.

    :param text: The string to parse.
    :type text: str

    :rtype: Parsed
    """
    _options = copy.copy(DEFAULT_OPTIONS)
    _options.update(options)

    return _normalize(_parse(text, **_options), **_options)


def _normalize(parsed, **options):
    """
    Normalizes the parsed element.

    :param parsed: The parsed elements.
    :type parsed: Parsed

    :rtype: Parsed
    """
    if options.get('exact'):
        return parsed

    if isinstance(parsed, time):
        now = options['now'] or datetime.now()

        return datetime(
            now.year, now.month, now.day,
            parsed.hour, parsed.minute, parsed.second,
            parsed.microsecond
        )
    elif isinstance(parsed, date) and not isinstance(parsed, datetime):
        return datetime(
            parsed.year, parsed.month, parsed.day
        )

    return parsed


def _parse(text, **options):
    # Trying to parse ISO8601
    try:
        return parse_iso8601(text)
    except ValueError:
        pass

    try:
        return _parse_common(text, **options)
    except ParserError:
        pass

    # We couldn't parse the string
    # so we fallback on the dateutil parser
    # If not strict
    if options.get('strict', True):
        raise ParserError(f'Unable to parse string [{text}]')

    try:
        dt = parser.parse(
            text,
            dayfirst=options['day_first'],
            yearfirst=options['year_first']
        )
    except ValueError:
        raise ParserError('Invalid date string: {}'.format(text))

    return dt


def _parse_common(text, **options):
    """
    Tries to parse the string as a common datetime format.

    :param text: The string to parse.
    :type text: str

    :rtype: dict or None
    """
    m = COMMON.match(text)
    has_date = False
    year = 0
    month = 1
    day = 1

    if not m:
        raise ParserError('Invalid datetime string')

    if m.group('date'):
        # A date has been specified
        has_date = True

        year = int(m.group('year'))

        if not m.group('monthday'):
            # No month and day
            month = 1
            day = 1
        else:
            if options['day_first']:
                month = int(m.group('day'))
                day = int(m.group('month'))
            else:
                month = int(m.group('month'))
                day = int(m.group('day'))

    if not m.group('time'):
        return date(year, month, day)

    # Grabbing hh:mm:ss
    hour = int(m.group('hour'))

    minute = int(m.group('minute'))

    second = int(m.group('second'))

    # Grabbing subseconds, if any
    microsecond = 0
    if m.group('subsecondsection'):
        # Limiting to 6 chars
        subsecond = m.group('subsecond')[:6]

        microsecond = int('{:0<6}'.format(subsecond))

    if has_date:
        return datetime(year, month, day, hour, minute, second, microsecond)

    return time(hour, minute, second, microsecond)
