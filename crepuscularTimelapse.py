#!/usr/bin/python
from picamera import PiCamera
import datetime
import timedir
import time
import pytz
from astral import Astral
import os

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
working_dir = ''
today = datetime.date.today()
now = pytz.utc.localize(datetime.datetime.utcnow())

print('Information for {0}/{1}'.format(city_name, city.region))
print('Latitude: {0}\tLongitude{1}'.format(city.latitude, city.longitude))
print('{0} seconds per exposure'.format(tl_interval))
print('{0} minutes pre-roll'.format(pre_roll))
print('{0} minutes post-roll'.format(post_roll))

for k, v in rec_dict.items():
    if v == True: print('Recording enabled for {0}'.format(k))

def get_timestamp():
    today = datetime.date.today()
    now = pytz.utc.localize(datetime.datetime.utcnow())
    return now, today

def set_time():
#    today = datetime.date.today()
#    now = pytz.utc.localize(datetime.datetime.utcnow())
    sun = city.sun(date=today, local=False)
    dawn = sun['dawn']
    sunrise = sun['sunrise']
    sunset = sun['sunset']
    dusk = sun['dusk']
    '''
    print('Dawn: {0}'.format(dawn))
    print('Sunrise: {0}'.format(sunrise))
    print('Sunset: {0}'.format(sunset))
    print('Dusk: {0}'.format(dusk))
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
    working_dir = getattr(timedir.nowdir(output_dir, scopelevel), scopedir)
    return working_dir

def tl_capture():
    sched_dict = set_time()
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
        print('Image recorded to {0} at {1}[UTC]'.format(fn, now))
        time.sleep(tl_interval)
        (roll, rec_sunrise_inprogress, rec_sunset_inprogress) = check_rolling()
        if roll == False: break
    return

def check_rolling():
    sched_dict = set_time()
    (now, today) = get_timestamp()
    rec_sunrise_inprogress = False
    rec_sunset_inprogress = False
    '''
    print('Today is {0}'.format(today))
    if rec_sunrise:
        print('Sunrise recording from {0} to {1}'.format(sched_dict['rec_start_sunrise'], sched_dict['rec_stop_sunrise']))
    if rec_sunset:
        print('Sunset recording from {0} to {1}'.format(sched_dict['rec_start_sunset'], sched_dict['rec_stop_sunset']))
    '''
    if rec_sunrise and (sched_dict['rec_start_sunrise'] < now < sched_dict['rec_stop_sunrise']):
        rolling = True
        rec_sunrise_inprogress = True
        print('Recording from {0} to {1}'.format(sched_dict['rec_start_sunrise'], sched_dict['rec_stop_sunrise']))
    elif rec_sunset and (sched_dict['rec_start_sunset'] < now < sched_dict['rec_stop_sunset']):
        rolling = True
        rec_sunset_inprogress = True
        print('Recording from {0} to {1}'.format(sched_dict['rec_start_sunset'], sched_dict['rec_stop_sunset']))
    else:
        rolling = False
        rec_sunrise_inprogress = False
        rec_sunset_inprogress = False

    return rolling, rec_sunrise_inprogress, rec_sunset_inprogress

try:
    while True:
        (rolling, rec_sunrise_inprogress, rec_sunset_inprogress) = check_rolling()
        if rolling: tl_capture()
        else: time.sleep(1)

except KeyboardInterrupt:
    print("Quit")
