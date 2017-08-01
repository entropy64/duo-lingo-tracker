"""Duo Lingo Progress Scraper

This module pulls progress data from the duo lingo API and generates a graph of your progress over time. 

"""
from datetime import datetime
import duolingo
import numpy as np
import os
import plotly.plotly as py
import plotly.graph_objs as go

duo_lingo_user_name = os.environ['DUO_LINGO_USER_NAME']
duo_lingo_password = os.environ['DUO_LINGO_PASSWORD']

lingoAPI = duolingo.Duolingo(duo_lingo_user_name, duo_lingo_password)

print lingoAPI.get_languages();

progress = lingoAPI.get_language_progress(u'de')

print progress

# =>
# {  
#  'streak':3,
#  'language_string':u'German',
#  'level_progress':724,
#  'level_percent':80,
#  'language':u'de',
#  'points_rank':3,
#  'fluency_score':0.20111657452535123,
#  'level':11,
#  'level_points':900,
#  'next_level':12,
#  'points':3724,
#  'num_skills_learned':47,
#  'level_left':176
#}

calendar = lingoAPI.get_calendar()

# =>
#[{u'datetime': 1500772136000.0, u'improvement': 10}, ...]

def calculate_metrics_inclusive_of_progress_points(points, calendar_metrics):
    """
    Args: 
        points (int): The language progress points
        calendar_metrics (list): The list of progress increments and their timestamps.

    Returns:
        list: The list of metrics updated.
    """


def calculate_metrics_from_calendar(data_points, period):
    """
    Args:
        data_points (list): List of namedtuples.
        period (str): The time period that each metric represents

    Returns:
        list: The list of metrics.
    """

def truncate_calendar_data_point_to_period(data_point, period):
    """
    Args:
        data_point (namedtuple): An individual calendar data point.
        period (str): The time period that each metric represents

    Returns:
        obj: The object.
    """

N = len(calendar)

x_axis = [ point[u'datetime'] for point in calendar]
y_axis = [ point[u'improvement'] for point in calendar ]

# Create a trace
trace = go.Scatter(
    x = x_axis,
    y = y_axis
)

data = [trace]

py.iplot(data, filename='basic-line')


