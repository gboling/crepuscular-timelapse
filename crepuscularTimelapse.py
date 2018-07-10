#!/usr/bin/python
from picamera import PiCamera
import datetime
import timedir
import time
import pytz
from astral import Astral
from os import system

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

print('Information for {0}/{1}'.format(city_name, city.region))
print('Latitude: {0}\tLongitude{1}'.format(city.latitude, city.longitude))
print('{0} seconds per exposure'.format(tl_interval))
print('{0} minutes pre-roll'.format(pre_roll))
print('{0} minutes post-roll'.format(post_roll))

for k, v in rec_dict.items():
    if v == True: print('Recording enabled for {0}'.format(k))

def set_time():
    today = datetime.date.today()
    now = pytz.utc.localize(datetime.datetime.utcnow())
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
            rec_start_sunrise, 'rec_stop_sunset': rec_stop_sunset}
    return sched_dict, now, today

def tl_capture():
    for filename in enumerate(
            camera.capture_continuous('image{counter:04d}.jpg')):
        (sched_dict, now, today) = set_time()
        (index, fn) = filename
        print('Image recorded to {0} at {1}[UTC]'.format(fn, now))
        time.sleep(tl_interval)
        roll = check_rolling()
        if roll == False: break
    return

def check_rolling():
    (sched_dict, now, today) = set_time()
    if rec_sunrise and (sched_dict['rec_start_sunrise'] < now < sched_dict['rec_stop_sunrise']):
        rolling = True
        print('Recording from {0} to {1}'.format(sched_dict['rec_start_sunrise'], sched_dict['rec_stop_sunrise']))
    elif rec_sunset and (sched_dict['rec_start_sunset'] < now < sched_dict['rec_stop_sunset']):
        rolling = True
        print('Recording from {0} to {1}'.format(sched_dict['rec_start_sunset'], sched_dict['rec_stop_sunset']))
    else:
        rolling = False

    return rolling

try:
    while True:
        rolling = check_rolling()
        if rolling: tl_capture()
        time.sleep(1)

except KeyboardInterrupt:
    print("Quit")


# system('convert -delay 10 -loop 0 image*.jpg animation.gif')
print('done')
