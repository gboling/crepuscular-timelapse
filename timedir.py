#!/usr/bin/env python

"""
To make a directory tree like thus: output_dir/year/month/day/hour/min
Also gets mtime of an arbitrary file and returns namedtuple for datetime and elements.
Returns a namedtuple with values for each level at time of function call.
by J. Grant Boling [gboling]at[gmail]dot[com]
"""

import time
import datetime
import os
import sys
import argparse

from collections import namedtuple

timedir_ntuple = namedtuple('timedir', 'yearDir monthDir dayDir hourDir minDir')
mtimedir_ntuple = namedtuple('mtimedir', 'yearDir monthDir dayDir hourDir minDir mtime mdtime')
output_dir = ''

def nowdir(output_dir, scopelevel):

    now = datetime.datetime.now()
    n_year = now.strftime('%Y')
    n_month = now.strftime('%m')
    n_day = now.strftime('%d')
    n_hour = now.strftime('%H')
    n_min = now.strftime('%M')
    year_dir = os.path.join(output_dir, n_year)
    month_dir = os.path.join(year_dir, n_month)
    day_dir = os.path.join(month_dir, n_day)
    hour_dir = os.path.join(day_dir, n_hour)
    min_dir = os.path.join(hour_dir, n_min)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if not os.path.exists(year_dir) and scopelevel >= 0:
        os.mkdir(year_dir)

    if not os.path.exists(month_dir) and scopelevel >= 1:
        os.mkdir(month_dir)

    if not os.path.exists(day_dir) and scopelevel >= 2:
        os.mkdir(day_dir)

    if not os.path.exists(hour_dir) and scopelevel >= 3:
        os.mkdir(hour_dir)

    if not os.path.exists(min_dir) and scopelevel == 4:
        os.mkdir(min_dir)

    return timedir_ntuple(year_dir, month_dir, day_dir, hour_dir, min_dir)

def mtimedir(mtime_file, mtoutput_dir):

    mtime_file_tail = os.path.dirname(mtime_file)
    mtime = os.path.getmtime(mtime_file)
    mdtime = datetime.datetime.fromtimestamp(mtime)
    m_year = mdtime.strftime('%Y')
    m_month = mdtime.strftime('%m')
    m_day = mdtime.strftime('%d')
    m_hour = mdtime.strftime('%H')
    m_min = mdtime.strftime('%M')
    mtyear_dir = os.path.join(mtoutput_dir, m_year)
    mtmonth_dir = os.path.join(mtyear_dir, m_month)
    mtday_dir = os.path.join(mtmonth_dir, m_day)
    mthour_dir = os.path.join(mtday_dir, m_hour)
    mtmin_dir = os.path.join(mthour_dir, m_min)

    return mtimedir_ntuple(mtyear_dir, mtmonth_dir, mtday_dir, mthour_dir, mtmin_dir, mtime, mdtime)

def main(output_dir):

    td_parser = argparse.ArgumentParser(description='Make a directory tree for year-month-day-hour-minute.')
    td_parser.add_argument('output_dir',
                            default=os.getcwd(),
                            help="Specify the base directory."
                            )
    td_parser.add_argument('-v', '--verbose',
                            dest="verbose",
                            default=False,
                            action='store_true',
                            )
    td_parser.add_argument('-s', '--scope',
                            dest="scope",
                            choices=["year", "month", "day", "hour", "min"],
                            default="day",
                            help="Specify how deep to make the directory tree."
                            )

    td_args = td_parser.parse_args()
    output_dir = td_args.output_dir

    if td_args.scope == "year": scopelevel = 0

    if td_args.scope == "month": scopelevel = 1

    if td_args.scope == "day": scopelevel = 2

    if td_args.scope == "hour": scopelevel = 3

    if td_args.scope == "min": scopelevel = 4

    nowdir(output_dir)

if __name__ == '__main__':

    main(output_dir)
