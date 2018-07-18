#!/usr/bin/python
from picamera import PiCamera
import datetime
import timedir
import time
import pytz
from astral import Astral
import os
from collections import namedtuple

import logging

import curses
import threading
from multiprocessing import Process


# Load the config file
config = {}
execfile("ctl.conf", config)

a = Astral()
city_name = config["city_name"]
city = a[city_name]
solar_depression = config["solar_depression"]
a.solar_depression = solar_depression
timezone = config["timezone"]
tz = pytz.timezone(timezone)


rec_sunrise = config["sunrise"]
rec_sunset = config["sunset"]
rec_dict = {'Sunrise':rec_sunrise, 'Sunset':rec_sunset}
# print(rec_dict)

CAM_RESOLUTION = config["resolution"]
camera = PiCamera()
camera.resolution = (CAM_RESOLUTION)
tl_interval = config["tl_interval"]
pre_roll = config["pre_roll"]
post_roll = config["post_roll"]
rolling = False
rec_sunrise_inprogress = False
rec_sunset_inprogress = False
scopelevel = 'day'
scopedir = 'dayDir'
output_dir = config["output_dir"]
logfile = config["logfile"]
loglevel = config["loglevel"]
numeric_level = getattr(logging, loglevel.upper(), None)
working_dir = ''
today = datetime.date.today()



def get_timestamp():
    today = datetime.date.today()
    now = pytz.utc.localize(datetime.datetime.utcnow())
    return now, today

def set_time(today):
    sun = city.sun(date=today, local=False)
    dawn = sun['dawn']
    sunrise = sun['sunrise']
    sunset = sun['sunset']
    dusk = sun['dusk']
    '''
    logging.debug('Dawn: {0} [UTC]'.format(dawn))
    logging.debug('Sunrise: {0} [UTC]'.format(sunrise))
    logging.debug('Sunset: {0} [UTC]'.format(sunset))
    logging.debug('Dusk: {0} [UTC]'.format(dusk))
    '''
    rec_start_sunrise = dawn - datetime.timedelta(minutes=pre_roll)
    rec_start_sunset = sunset - datetime.timedelta(minutes=pre_roll)
    rec_stop_sunrise = sunrise + datetime.timedelta(minutes=post_roll)
    rec_stop_sunset = dusk + datetime.timedelta(minutes=post_roll)
    sched_dict = {'dawn': dawn, 'sunrise': sunrise, 'sunset': sunset,
            'dusk': dusk, 'rec_start_sunrise': rec_start_sunrise,
            'rec_start_sunset': rec_start_sunset, 'rec_stop_sunrise':
            rec_stop_sunrise, 'rec_stop_sunset': rec_stop_sunset}
    return sched_dict

def buildOutputDir():
    """Make year/month/day directory and export a variable of the day's directory"""
#    working_dir = getattr(timedir.nowdir(output_dir, scopelevel), scopedir)
    td = timedir.nowdir(output_dir, 2)
    working_dir = td.dayDir
    return working_dir

def init_window(stdscr):
    k = 0
    cursor_x = 0
    cursor_y = 0

    #curses.noecho()
    stdscr.clear()
    stdscr.refresh()

    k = 0
    cursor_x = 0
    cursor_y = 0

    curses.start_color()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)

    scr_dict = {'k': k, 'cursor_x': cursor_x, 'cursor_y': cursor_y}

    return scr_dict


def draw_window(stdscr):
    while True:
        (k, cursor_x, cursor_y) = init_window(stdscr)

        stdscr.clear()
        now = datetime.datetime.now()
        today = datetime.date.today()
        sched_dict = set_time(today)
        height, width = stdscr.getmaxyx()
        '''
        if k == curses.KEY_DOWN:
            cursor_y = cursor_y + 1
        elif k == curses.KEY_UP:
            cursor_y = cursor_y - 1
        elif k == curses.KEY_RIGHT:
            cursor_x = cursor_x + 1
        elif k == curses.KEY_LEFT:
            cursor_x = cursor_x - 1
        '''

        cursor_x = max(0, cursor_x)
        cursor_x = min(width-1, cursor_x)

        cursor_y = max(0, cursor_y)
        cursor_y = min(height-1, cursor_y)

        # Title, Time, and Menu Bar -- Top Line
        title = 'crepuscular-timelapse'
        ts = now.strftime('%Y-%m-%d %H-%M-%S')
        tspos = width - len(ts)
        stdscr.addstr(0, 0, title, curses.color_pair(1))
        stdscr.addstr(0, tspos, ts, curses.color_pair(1))

        # Location Info

        # Today's Recording Schedule

        # File List

        # Status Bar -- Bottom Line
        statusbarstr = 'Press Ctrl-C to exit | {0} Images Recorded Today'
        k = stdscr.getch()

        #recswitch()

        stdscr.refresh()

    return

def tl_capture():
    (now, today) = get_timestamp()
    sched_dict = set_time(today)
    working_dir = buildOutputDir()
    (roll, rec_sunrise_inprogress, rec_sunset_inprogress) = check_rolling()
    fn_format = os.path.join(working_dir, 'tl-{timestamp:%Y%m%d}-{counter:04d}.jpg')
    if rec_sunrise_inprogress:
        fn_format = os.path.join(working_dir, 'dawn-{timestamp:%Y%m%d}-{counter:04d}.jpg')
    elif rec_sunset_inprogress:
        fn_format = os.path.join(working_dir, 'dusk-{timestamp:%Y%m%d}-{counter:04d}.jpg')
    for filename in enumerate(
            camera.capture_continuous(fn_format)):
        (index, fn) = filename
        (now, today) = get_timestamp()

        logging.info('Image recorded to {0} at {1} [UTC]'.format(fn, now))

        time.sleep(tl_interval)
#        curses.wrapper(draw_window)
        (roll, rec_sunrise_inprogress, rec_sunset_inprogress) = check_rolling()
        if roll == False: break
    return

def check_rolling():
    (now, today) = get_timestamp()
    sched_dict = set_time(today)
    rec_sunrise_inprogress = False
    rec_sunset_inprogress = False

    logging.debug('Today is {0}'.format(today))
    '''
    if rec_sunrise:
        logging.debug('Sunrise recording from {0} to {1} [UTC]'.format(sched_dict['rec_start_sunrise'], sched_dict['rec_stop_sunrise']))
    if rec_sunset:
        logging.debug('Sunset recording from {0} to {1} [UTC]'.format(sched_dict['rec_start_sunset'], sched_dict['rec_stop_sunset']))
    '''
    if rec_sunrise and (sched_dict['rec_start_sunrise'] < now < sched_dict['rec_stop_sunrise']):
        rolling = True
        rec_sunrise_inprogress = True
        logging.debug('Recording from {0} to {1} [UTC]'.format(sched_dict['rec_start_sunrise'], sched_dict['rec_stop_sunrise']))
    elif rec_sunset and (sched_dict['rec_start_sunset'] < now < sched_dict['rec_stop_sunset']):
        rolling = True
        rec_sunset_inprogress = True
        logging.debug('Recording from {0} to {1} [UTC]'.format(sched_dict['rec_start_sunset'], sched_dict['rec_stop_sunset']))

    else:
        rolling = False
        rec_sunrise_inprogress = False
        rec_sunset_inprogress = False

    return rolling, rec_sunrise_inprogress, rec_sunset_inprogress

def recswitch():
    (rolling, rec_sunrise_inprogress, rec_sunset_inprogress) = check_rolling()
    logging.debug('rolling: {0}\trec_sunrise_inprogress: {1}\trec_sunset_inprogress: {2}'.format(
        rolling, rec_sunrise_inprogress, rec_sunset_inprogress))
    if rolling: tl_capture()
    else:
        time.sleep(1)

    return

def main():
    logging.basicConfig(filename=logfile,
        format='%(levelname)s:%(message)s', level=numeric_level)


    logging.info('Information for {0}/{1}'.format(city_name, city.region))
    logging.info('Latitude: {0}\tLongitude{1}'.format(city.latitude, city.longitude))
    logging.info('{0} seconds per exposure'.format(tl_interval))
    logging.info('{0} minutes pre-roll'.format(pre_roll))
    logging.info('{0} minutes post-roll'.format(post_roll))

    for k, v in rec_dict.items():
        if v == True: logging.info('Recording enabled for {0}'.format(k))

    #curses.wrapper(init_window)
    rs = threading.Thread(target=recswitch)
    rs.start()

    dw = threading.Thread(target=curses.wrapper(draw_window))
    dw.start()
    '''

    Process(target=curses.wrapper(draw_window)).start()
    Process(target=recswitch).start()
    '''
#    recswitch()
#    curses.wrapper(draw_window)
    return


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Quit")
