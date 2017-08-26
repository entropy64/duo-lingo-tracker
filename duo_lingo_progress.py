"""
Duo Lingo Long Term Improvement Tracker
duo_lingo_user_name = os.environ['DUO_LINGO_USER_NAME']
duo_lingo_password = os.environ['DUO_LINGO_PASSWORD']

This module pulls progress data from the duo lingo API and generates a graph of your progress over time.
"""
from collections import deque
from delorean import Delorean
from datetime import datetime
import duolingo
from functools import reduce
import itertools
from operator import itemgetter
import json
import os
import plotly.plotly as py
import plotly.graph_objs as go


def merge_dictionaries_by(key, combine):
    """Returns a function that merges two dictionaries.
       The dictionaries are assumed to have the same value for the
       same key.  For all other keys, the values are combined
       using the specified binary operator.
    Args:
        key (string): The dictionary key to use as the id
        combine (callable): The function to handle the merge
    Returns:
        (dict): The result of the merge
    """
    return lambda dictionary1, dictionary2: {
        k: dictionary1[k] if k == key else combine(dictionary1[k], dictionary2[k])
        for k in dictionary1
    }


def create_merger_of_list_of_dictionaries_by(key, combine):
    """Returns a function that merges a list of records, grouped by
       the specified key, with values combined using the specified
       binary operator. Curry-able.
    Args:
        key (string): The dictionary key to use as the id
        combine (callable): The function to handle the merge
    Returns:
        (callable): The function that will handle the merge.
    """
    key_prop = itemgetter(key)
    return lambda lst: [
        reduce(merge_dictionaries_by(key, combine), records)
        for _, records in itertools.groupby(sorted(lst, key=key_prop), key_prop)
    ]


def get_db_filename():
    """
    Returns:
        string: The filename / path to the db.json file
    """
    directory_path = os.path.dirname(os.path.realpath(__file__))
    path = os.path.expanduser(directory_path + '/data/')
    return path + 'db.json'


def write_db(filename, data):
    """
    Args:
        filename (string): The file name as a path
        data (object): The object data to persist
    """
    with open(filename, 'w') as f:
        json.dump(data, f)


def read_db(filename):
    """
    Args:
        filename (string): The file name as a path
    Returns:
        object: The data as JSON.
    """
    with open(filename, 'r') as f:
        j = json.load(f)
        return dict(j)


def create_db_user_entry(username, languages):
    """
    Args:
        username (string): The duo-lingo username
        languages (list): The list of languages. See #create_language
    Returns:
        object: The json structure ready for persisting to db.json
    """
    db = {
        "languages": {}
    }

    for l in languages:
        for key in l.keys():
            db['languages'][key] = l[key]

    return db


def calculate_metrics_from_improvements(data_points, period):
    """
    Args:
        data_points (list): List of namedtuples.
        period (string): The time period that each metric represents

    Returns:
        list: The list of metrics.
    """
    truncated_data_points = [
        truncate_calendar_data_point_to_period(p, period) for p in data_points
    ]

    get_attr = (lambda o: o['datetime'])
    groups = [list(g) for k, g in itertools.groupby(sorted(truncated_data_points, key=get_attr), get_attr)]

    return map((lambda group: create_metric_from_group(group)), groups)


def create_metric_from_group(group):
    """
    Args:
        group (list): The list of improvement points with a common timestamp

    Returns:
        object:
    """
    timestamp = group[0]['datetime']
    group_improvement = sum(i['improvement'] for i in group)

    return {
        'datetime': timestamp,
        'improvement': group_improvement
    }


def truncate_calendar_data_point_to_period(data_point, period):
    """
    Args:
        data_point (object): An individual calendar data point.
        period (string): The time period that each metric represents

    Returns:
        obj: The object.
    """
    date_time = datetime.fromtimestamp(int(data_point['datetime'] / 1000))
    truncated = Delorean(date_time, timezone='UTC').truncate(period).datetime
    formatted = truncated.strftime('%Y-%m-%dT%H:%M:%S')

    return {
        'datetime': formatted,
        'improvement': data_point['improvement']
    }


def accumulate_progress(improvements, latest_experience_score):
    """
    Args:
        improvements (list):
        latest_experience_score (int):
    Returns:
        list: The running totals as a list.
    """
    running_total = latest_experience_score
    cumulative_progress = deque([latest_experience_score])

    for i in improvements[::-1]:
        running_total -= i
        cumulative_progress.appendleft(running_total)

    return cumulative_progress


def create_language(language_two_letter_key, current_progress, improvements):
    """
    Args:
        language_two_letter_key (string): eg. German is 'de'
        current_progress (object): The object returned from the duo lingo API (get_language_progress(key))
        improvements (list): The list of improvements (datetime, improvement)
    Returns:
        object: The language object for the db.json
    """
    language = {
        language_two_letter_key: {
            "progress": current_progress,
            "improvements": []
        }
    }

    for i in improvements:
        language[language_two_letter_key]['improvements'].append(i)

    return language


def get_language_improvements(client, language):
    """
    Args:
        client (Duolingo):
        language (string):
    Returns:
         (object):
    """
    language_details = client.get_language_details(language)
    language_abbreviation = language_details[u'language']
    language_progress = {}
    if language_details['current_learning']:
        language_progress = client.get_language_progress(language_abbreviation)

    latest_improvements = client.get_calendar()

    # Persist data to JSON file
    language_entry = create_language(language_abbreviation, language_progress, latest_improvements)

    return language_entry


def check_if_key_exists(dictionary, key):
    try:
        value = dictionary[key]
        return True
    except KeyError:
        # Key is not present
        return False


def create_trace_for_friend(friend, database_json):
    """
    Args:
        friend (object): The username of the friend.
        database_json (object): The database history as an object
    Returns:
         (list): the list of progress improvements for the given friend across languages
    """
    points = friend['points']
    friend_username = friend['username']
    friend_lingo_client = duolingo.Duolingo(friend_username)
    languages = friend_lingo_client.get_languages()

    language_entries = [get_language_improvements(friend_lingo_client, lang) for lang in languages]
    updated_languages = []
    saved_languages = {}
    if check_if_key_exists(database_json, friend_username):
        saved_languages = database_json[friend_username]['languages']

    friend_improvements = []
    historical_improvements = []
    for entry in language_entries:
        updated_entry = {}
        for key in entry.keys():
            friend_improvements.append(entry[key]['improvements'])
            if not check_if_key_exists(saved_languages, key):
                updated_entry[key] = {
                    'progress': entry[key]['progress'],
                    'improvements': entry[key]['improvements']
                }
                updated_languages.append(updated_entry)
                continue

            selected_language = saved_languages[key]
            historical_improvements_for_language = selected_language['improvements']
            historical_improvements.append(historical_improvements_for_language)
            updated_entry[key] = {
                'progress': entry[key]['progress'],
                'improvements': historical_improvements_for_language + entry[key]['improvements']
            }
            updated_languages.append(updated_entry)

    flat_list = sum(friend_improvements, [])
    flattened_historical_improvements = sum(historical_improvements, [])

    merger_function = create_merger_of_list_of_dictionaries_by('datetime', (lambda a, b: a))

    combined_improvements = merger_function(flattened_historical_improvements + flat_list)

    user = create_db_user_entry(friend_username, updated_languages)
    database_json[friend_username] = user

    write_db(get_db_filename(), database_json)

    formatted_calendar = calculate_metrics_from_improvements(combined_improvements, 'day')

    # todo: replace the last calendar item with the current value
    # todo: then map over this from the back of the list
    # todo: subtracting the calendar improvement from the running total
    progress_improvements = [point['improvement'] for point in formatted_calendar]

    x_axis = [point['datetime'] for point in formatted_calendar]
    y_axis = list(accumulate_progress(progress_improvements, points))[1:]

    return go.Scatter(
        x=x_axis,
        y=y_axis,
        mode="lines+markers",
        name="{0} - {1}".format(friend_username, 'Total Progress')
    )


if __name__ == '__main__':
    duo_lingo_user_name = os.environ['DUO_LINGO_USER_NAME']
    duo_lingo_password = os.environ['DUO_LINGO_PASSWORD']
    lingoAPI = duolingo.Duolingo(duo_lingo_user_name, duo_lingo_password)

    # Read in the previously saved data
    db_json = read_db(get_db_filename())

    # fetch friends (includes you) and create plot traces of their progress
    friends = lingoAPI.get_friends()
    friend_traces = [create_trace_for_friend(f, db_json) for f in friends]

    layout = go.Layout(
        title='Duo Lingo - Language Progress',
        xaxis=dict(
            title='Time'
        ),
        yaxis=dict(
            title='Language Experience'
        )
    )

    figure = go.Figure(data=friend_traces, layout=layout)

    # Finally create/update web plot
    try:
        py.plot(figure, filename='basic-line')
    except Exception, e:
        print e
