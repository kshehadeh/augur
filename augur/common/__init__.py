import os
import re
import string

import arrow
import datetime
import pytz

import augur

__author__ = 'karim'


import comm
import const
import serializers
import formatting

from math import sqrt
from dateutil.parser import parse

import const

JIRA_KEY_REGEX = r"([A-Za-z]+\-\d{1,6})"

COMPLETE_STATUSES = ["complete","resolved"]
POSITIVE_RESOLUTIONS = ["fixed", "done", "deployed"]
_CACHE = {}

# Note: The order matters in this list.  Time based matches are first to ensure that
#   the time is not truncated in cases where date matches are found then the rest of the
#   list is skipped.
POSSIBLE_DATE_TIME_FORMATS = [
    "YYYY-MM-DD HH:mm",
    "MM-DD-YYYY HH:mm",
    "MM/DD/YYYY HH:mm",
    "YYYY/MM/DD HH:mm",
    "MM/DD/YYYY HH:mm",
    "M/D/YYYY HH:mm",
    "M/D/YY HH:mm",
]

POSSIBLE_DATE_FORMATS = [
    "YYYY-MM-DD",
    "MM-DD-YYYY",
    "MM/DD/YYYY",
    "YYYY/MM/DD",
    "M/D/YYYY",
    "M/D/YY",
]

SITE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))


class Struct:
    """
        Create objects out of dictionaries like this:
        >>> d = {"test":1,"foo":"bar"}
        >>> s = Struct(**d)
        >>> s.test
    """
    def __init__(self, **entries):
        self.__dict__.update(entries)


def remove_null_fields(d):
    """
    Takes a dictionary and returns a new dictionary with fields that have null values.
    :param d: A dictionary to remove null fields from
    :return:
    """
    return dict((k, v) for k, v in d.iteritems() if v is not None)


def clean_issue(issue):
    """
    This will put commonly used fields at the root of the dictionary and remove all of the custom fields that are
    empty.
    :param issue: A dict that is the the issue to clean
    :return: Returns a dictionary.
    """
    points_field_name = augur.api.get_issue_field_from_custom_name('Story Points')
    points = augur.common.deep_get(issue, 'fields', points_field_name)
    status = augur.common.deep_get(issue, 'fields', 'status', 'name') or ''
    resolution = augur.common.deep_get(issue, 'fields', 'resolution', 'name') or ''
    return {
        'key': issue['key'],
        'summary': augur.common.deep_get(issue, 'fields', 'summary'),
        'assignee': augur.common.deep_get(issue, 'fields', 'assignee', 'name') or 'unassigned',
        'description': augur.common.deep_get(issue, 'fields', 'description'),
        'fields': remove_null_fields(issue['fields']),
        'points': float(points if points else 0.0),
        'status': status.lower(),
        'changelog': augur.common.deep_get(issue,'changelog'),
        'resolution': resolution.lower(),
    }


def find_team_name_in_string(team_name, string_to_search):
    """
    Utility that searches the given string for the given team name.  It does the work of stripping out the
    word "Team" from the team_name for you so it's more permissive than just doing a substring search.

    :param team_name: The name of the team
    :param string_to_search: The source string to search for the team name
    :return: Returns the True if the name was found, False otherwise.
    """
    # Remove the word "Team" from the team name (if necessary)
    team_replace = re.compile(re.escape('team'), re.IGNORECASE)
    team_name = team_replace.sub('', team_name).strip()
    return team_name.lower() in string_to_search.lower()


def utc_to_local(utc_dt):
    local_tz = pytz.timezone('America/New_York')
    return utc_dt.replace(tzinfo=pytz.utc).astimezone(local_tz)


def extract_jira_tickets(text):
    """
    Gets a list of all the JIRA keys found in the given text
    :param text: The string to search
    :return: A list of strings
    """
    match = re.search(JIRA_KEY_REGEX,text)
    return match.groups() or []


def transform_status_string(status):
    return status.lower().replace(' ','_')


def get_week_range(date):
    """
    This will return the start and end of the week in which the given date resides.
    :param date: The source date
    :return: A tuple containing the start and end date of the week (in that order)
    """
    start = date - datetime.timedelta(days=date.weekday())
    end = start + datetime.timedelta(days=6)
    return start,end


def standard_deviation(lst,population=True):

    sd = 0

    try:
        num_items = len(lst)

        if num_items == 0:
            return 0

        mean = sum(lst) / num_items
        differences = [x - mean for x in lst]
        sq_differences = [d ** 2 for d in differences]
        ssd = sum(sq_differences)

        if population is True:
            variance = ssd / num_items
        elif num_items > 1:
            variance = ssd / (num_items - 1)
        else:
            variance = 0

        sd = sqrt(variance)

    except Exception, e:
        print "Problem during calculation of standard deviation: %s"%e.message

    return sd


def get_date_range_from_query_params(request,default_start=None,default_end=None):
    start = request.GET.get('start', None)
    end = request.GET.get('end', None)
    return get_date_range_from_strings(start,end,default_start,default_end)


def get_date_range_from_strings(start,end, default_start=None, default_end=None):
    if not start:
        # Don't go back further than 90 days for the sake of performance and storage.
        start = default_start
    else:
        start = arrow.get(start, "YYYY-MM-DD").floor('day')

    if not end:
        end = default_end
    else:
        end = arrow.get(end, "YYYY-MM-DD").ceil('day')

    return start,end


def deep_get(dictionary, *keys):
    """
    Retrieves a deeply nested dictionary key checking for existing keys along the way.  
    Returns None if any key is not found.
    :param dictionary: The dictionary to retrieve the data from.
    :param default: The default value to return if there is a problem during the search
    :param keys: Ordered parameters representing the keys (in the order they should be referenced)
    :return: Returns the value if found, None otherwise.
    """
    default = None
    return reduce(lambda d, key: d.get(key) if d else default, keys, dictionary)


def calc_weekends(start_day, end_day):
    """
    Calculate the number of weekends in a given date range.
    :param start_day: Start of the range (datetime)
    :param end_day: End of the range  (datetime)
    :return: Returns the number of weekend
    """
    duration = end_day - start_day
    days_until_weekend = [5, 4, 3, 2, 1, 1, 6]
    adjusted_duration = duration - days_until_weekend[start_day]
    if adjusted_duration < 0:
        weekends = 0
    else:
        weekends = (adjusted_duration/7)+1
    if start_day == 5 and duration % 7 == 0:
        weekends += 1
    return weekends


def clean_detailed_sprint_info(sprint_data):
    """
    Takes the given sprint object and cleans it up to replace the date time values to actual python datetime objects.
    :param sprint_data:
    :return:
    """
    # convert date strings to dates
    for key, value in sprint_data['sprint'].iteritems():
        if key in ['startDate', 'endDate', 'completeDate']:
            try:
                sprint_data['sprint'][key] = parse(value)
            except ValueError:
                sprint_data['sprint'][key] = None

