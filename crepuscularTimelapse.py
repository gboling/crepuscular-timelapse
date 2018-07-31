#!/usr/bin/python
from picamera import PiCamera
import datetime
import timedir
import time
import pytz
from astral import Astral
import os
import sys
from collections import namedtuple

import logging

import curses
import threading
import Queue


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
headless = config["headless"]
numeric_level = getattr(logging, loglevel.upper(), None)
working_dir = ''
today = datetime.date.today()

fn_q = Queue.Queue()

threadLock = threading.RLock()
global_counter = 0

_QUIT = False


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
    td = timedir.nowdir(output_dir, 2)
    working_dir = td.dayDir
    return working_dir

def init_window(stdscr):
    k = 0
    cursor_x = 0
    cursor_y = 0

    stdscr.erase()
    stdscr.refresh()
    curses.noecho()
    curses.curs_set(0)
    # Don't wait for getch() to refresh the screen
    stdscr.nodelay(1)


    k = 0
    cursor_x = 0
    cursor_y = 0

    curses.start_color()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_GREEN)
    curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(6, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(7, curses.COLOR_WHITE, curses.COLOR_RED)

    scr_dict = {'k': k, 'cursor_x': cursor_x, 'cursor_y': cursor_y}

    return scr_dict


def draw_window(stdscr):
    global _QUIT
    (k, cursor_x, cursor_y) = init_window(stdscr)
    height, width = stdscr.getmaxyx()
    one_third_pos = (width // 3)
    two_thirds_pos = width - (width//3)
    centered = (width // 2)
    fn_row = 0
    filewin_h = (height - 4)
    filewin_w = (two_thirds_pos - 5)
    filewin = stdscr.subwin(filewin_h, filewin_w, 2, 2)
    file_rows, file_columns = filewin.getmaxyx()
    file_rows -= 1
    fn_list = []
    while not _QUIT:

        # erase instead of clear to avoid flicker
        stdscr.erase()
        filewin.erase()
        now = datetime.datetime.now()
        today = datetime.date.today()
        sched_dict = set_time(today)



        # Title, Time, and Menu Bar -- Top Line
        title = 'crepuscular-timelapse'
        fmtz = '%H:%M:%S %Z%z'
        fmt = '%H:%M:%S'
        ts = now.strftime(fmt)
        tspos = (width - len(ts)) - 1
        stdscr.attron(curses.A_BOLD)
        stdscr.addstr(0, 0, title, curses.color_pair(1))
        stdscr.addstr(0, tspos, ts, curses.color_pair(1))
        stdscr.attroff(curses.A_BOLD)

        # Location Info
        city_name_disp = "City: " + city_name
        lat_disp = "Latitude: " + str(city.latitude)
        long_disp = "Longitude: " + str(city.longitude)
        solar_dep_disp = "Solar Depression: " + solar_depression.capitalize()
        pre_disp = "Pre-Roll: " + str(pre_roll) + " minutes"
        post_disp = "Post-Roll: " + str(post_roll) + " minutes"
        stdscr.addstr(2, two_thirds_pos, city_name_disp, curses.color_pair(1))
        stdscr.addstr(3, two_thirds_pos, lat_disp, curses.color_pair(5))
        stdscr.addstr(4, two_thirds_pos, long_disp, curses.color_pair(5))
        stdscr.addstr(5, two_thirds_pos, solar_dep_disp, curses.color_pair(6))
        stdscr.addstr(6, two_thirds_pos, pre_disp, curses.color_pair(2))
        stdscr.addstr(7, two_thirds_pos, post_disp, curses.color_pair(2))

        # Today's Recording Schedule
        sunrise_start_local = (
                sched_dict['rec_start_sunrise']).astimezone(tz)
        sunrise_stop_local = (
                sched_dict['rec_stop_sunrise']).astimezone(tz)
        sunset_start_local = (
                sched_dict['rec_start_sunset']).astimezone(tz)
        sunset_stop_local = (
                sched_dict['rec_stop_sunset']).astimezone(tz)

        sunrise_start_local_disp = sunrise_start_local.strftime(fmtz)
        sunrise_stop_local_disp = sunrise_stop_local.strftime(fmtz)
        sunset_start_local_disp = sunset_start_local.strftime(fmtz)
        sunset_stop_local_disp = sunset_stop_local.strftime(fmtz)

        rec_section_title = "Today's Recording Schedule"
        rec_section_title2 = "Including pre and postroll"
        rec_section_title_pad = '{:^32}'.format(rec_section_title)
        rec_section_title2_pad = '{:^32}'.format(rec_section_title2)
        dawn_disp = "Dawn:    " + str(sunrise_start_local_disp)
        sunrise_disp = "Sunrise: " + str(sunrise_stop_local_disp)
        sunset_disp = "Sunset:  " + str(sunset_start_local_disp)
        dusk_disp = "Dusk:    " + str(sunset_stop_local_disp)

        rec_section_width = len(rec_section_title)
        dawn_disp_pad = dawn_disp.ljust(rec_section_width)
        sunrise_disp_pad = sunrise_disp.ljust(rec_section_width)
        sunset_disp_pad = sunset_disp.ljust(rec_section_width)
        dusk_disp_pad = dusk_disp.ljust(rec_section_width)

        stdscr.addstr(10, two_thirds_pos, rec_section_title_pad, curses.color_pair(3))
        stdscr.addstr(11, two_thirds_pos, rec_section_title2_pad, curses.color_pair(3))
        stdscr.addstr(12, two_thirds_pos, dawn_disp_pad, curses.color_pair(4))
        stdscr.addstr(13, two_thirds_pos, sunrise_disp_pad, curses.color_pair(7))
        stdscr.addstr(14, two_thirds_pos, sunset_disp_pad, curses.color_pair(4))
        stdscr.addstr(15, two_thirds_pos, dusk_disp_pad, curses.color_pair(7))

        # File List 
        # Subwin seems to be the best bet for a scrollable buffer

        fn_row = 1
        fw_canvas_h = (filewin_h - 2)
        fn_q_count = len(fn_list)
        if not fn_q.empty():
            fn_q_out = fn_q.get()
            fn_list.append(fn_q_out)
        if fn_q_count < fw_canvas_h:
            for item in fn_list:
                if fn_row <= fw_canvas_h:
                    filewin.addstr(fn_row, 1, item)
                    fn_row += 1
        else:
            for item in fn_list[(fw_canvas_h * -1):]:
                filewin.addstr(fn_row, 1, item)
                fn_row += 1


        filewin.box()

        # Recording Indicators
        start = "START"
        stop = "STOP"
        start_pad = start.rjust(6)
        stop_pad = stop.rjust(6)
        (rolling, rec_sunrise_inprogress, rec_sunset_inprogress) = check_rolling()
        rec_status = "RECORDING IN PROGRESS"
        rec_indc_pos = two_thirds_pos + rec_section_width
        if rec_sunrise:
            stdscr.addstr(12, (rec_indc_pos), start_pad, curses.color_pair(4))
            stdscr.addstr(13, (rec_indc_pos), stop_pad, curses.color_pair(7))
        if rec_sunset:
            stdscr.addstr(14, (rec_indc_pos), start_pad, curses.color_pair(4))
            stdscr.addstr(15, (rec_indc_pos), stop_pad, curses.color_pair(7))
        if rolling:
            stdscr.addstr(17, two_thirds_pos, rec_status, curses.color_pair(7))


        # Status Bar -- Bottom Line
        sbar_qmesg = "| Press q to exit |"
        with threadLock:
            sbar_imgcount = "| {0} Images Recorded Since Launch |".format(global_counter)
        sbar_dfree = "| {0}% Free Space |"

        stat_centered = (centered - (len(sbar_dfree) // 2))
        stat_rjust = (width - len(sbar_dfree)) - 1

        # (Height - 1) to avoid problems with byobu
        stdscr.addstr((height - 1), 0, sbar_qmesg)
        stdscr.addstr((height - 1), stat_centered, sbar_imgcount)
        stdscr.addstr((height - 1), stat_rjust, sbar_dfree)

        # Deal with user input
        k = stdscr.getch()

        if k == ord('q'):
            _QUIT = True

        #stdscr.refresh()
        filewin.refresh()
        if _QUIT:
            break
        curses.napms(50)

    return

def tl_capture():
    global global_counter
    (now, today) = get_timestamp()
    sched_dict = set_time(today)
    working_dir = buildOutputDir()
    (roll, rec_sunrise_inprogress, rec_sunset_inprogress) = check_rolling()
    if rec_sunrise_inprogress:
        working_dir_dawn = os.path.join(working_dir, 'dawn')
        if not os.path.exists(working_dir_dawn):
            os.mkdir(working_dir_dawn)
        fn_format = os.path.join(working_dir_dawn, 'dawn-{timestamp:%Y%m%d}-{counter:04d}.jpg')
    elif rec_sunset_inprogress:
        working_dir_dusk = os.path.join(working_dir, 'dusk')
        if not os.path.exists(working_dir_dusk):
            os.mkdir(working_dir_dusk)
        fn_format = os.path.join(working_dir_dusk, 'dusk-{timestamp:%Y%m%d}-{counter:04d}.jpg')
    for filename in enumerate(
            camera.capture_continuous(fn_format)):
        (index, fn) = filename
        (now, today) = get_timestamp()
        loc_now = datetime.datetime.now()
        fmt = '%H:%M:%S'
        ts = loc_now.strftime(fmt)

        logging.info('Image recorded to {0} at {1} [UTC]'.format(fn, now))

        fn_q.put('{0} at {1}'.format(fn, ts))
        (roll, rec_sunrise_inprogress, rec_sunset_inprogress) = check_rolling()
        with threadLock:
            global_counter += 1
        if roll == False: break
        if _QUIT:
            break
        time.sleep(tl_interval)
    return

def check_rolling():
    (now, today) = get_timestamp()
    sched_dict = set_time(today)
    rec_sunrise_inprogress = False
    rec_sunset_inprogress = False

    if rec_sunrise and (sched_dict['rec_start_sunrise'] < now < sched_dict['rec_stop_sunrise']):
        rolling = True
        rec_sunrise_inprogress = True
    elif rec_sunset and (sched_dict['rec_start_sunset'] < now < sched_dict['rec_stop_sunset']):
        rolling = True
        rec_sunset_inprogress = True

    else:
        rolling = False
        rec_sunrise_inprogress = False
        rec_sunset_inprogress = False

    return rolling, rec_sunrise_inprogress, rec_sunset_inprogress

def recswitch():
    while True:
        (rolling, rec_sunrise_inprogress, rec_sunset_inprogress) = check_rolling()
        logging.debug('rolling: {0}\trec_sunrise_inprogress: {1}\trec_sunset_inprogress: {2}'.format(
            rolling, rec_sunrise_inprogress, rec_sunset_inprogress))
        if rolling: tl_capture()
        else:
            time.sleep(1)
        if _QUIT:
            break

    return

def main():
    global rs
    logging.basicConfig(filename=logfile,
        format='%(levelname)s:%(message)s', level=numeric_level)


    logging.info('Information for {0}/{1}'.format(city_name, city.region))
    logging.info('Latitude: {0}\tLongitude{1}'.format(city.latitude, city.longitude))
    logging.info('{0} seconds per exposure'.format(tl_interval))
    logging.info('{0} minutes pre-roll'.format(pre_roll))
    logging.info('{0} minutes post-roll'.format(post_roll))

    for k, v in rec_dict.items():
        if v == True: logging.info('Recording enabled for {0}'.format(k))

    rs = threading.Thread(target=recswitch)
    rs.setDaemon(True)
    rs.start()
    if not headless:
        curses.wrapper(draw_window)
    if _QUIT:
        rs.join()
        print("Quit")

    return


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Quit")
        rs.join()
