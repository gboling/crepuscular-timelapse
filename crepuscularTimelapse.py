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
timezone = config["timezone"]
tz = pytz.timezone(timezone)


rec_dawn = config["dawn"]
rec_dusk = config["dusk"]
rec_sunrise = config["sunrise"]
rec_sunset = config["sunset"]
rec_dict = {'Dawn':rec_dawn, 'Dusk':rec_dusk, 'Sunrise':rec_sunrise, 'Sunset':rec_sunset}
# print(rec_dict)

CAM_RESOLUTION = config["resolution"]
camera = PiCamera()
camera.resolution = (CAM_RESOLUTION)
tl_interval = config["tl_interval"]
rec_time = config["rec_time"]
rolling = False

print('Information for {0}/{1}'.format(city_name, city.region))
print('Latitude: {0}\tLongitude{1}'.format(city.latitude, city.longitude))
print('{0} seconds per exposure'.format(tl_interval))
print('{0} minutes total time lapse'.format(rec_time))

for k, v in rec_dict.items():
    if v == True: print('Recording enabled for {0}'.format(k))

def set_time():
    today = datetime.date.today()
    now = pytz.utc.localize(datetime.datetime.utcnow())
    sun = city.sun(date=today, local=False)
    # rewrite the following to use the builtin sun_utc dict object
    dawn = sun['dawn']
    sunrise = sun['sunrise']
    noon = sun['noon']
    sunset = sun['sunset']
    dusk = sun['dusk']
    rec_cutoff_dawn = dawn + datetime.timedelta(minutes=rec_time)
    rec_cutoff_sunrise = sunrise + datetime.timedelta(minutes=rec_time)
    rec_cutoff_noon = noon + datetime.timedelta(minutes=rec_time)
    rec_cutoff_sunset = sunset + datetime.timedelta(minutes=rec_time)
    rec_cutoff_dusk = dusk + datetime.timedelta(minutes=rec_time)
    sched_dict = {'dawn': dawn, 'sunrise': sunrise, 'noon': noon, 'sunset': sunset,
            'dusk': dusk, 'rec_cutoff_sunrise': rec_cutoff_sunrise, 'rec_cutoff_dawn':
            rec_cutoff_dawn, 'rec_cutoff_noon': rec_cutoff_noon, 'rec_cutoff_sunset':
            rec_cutoff_sunset, 'rec_cutoff_dusk': rec_cutoff_dusk}
    return sched_dict, now, today

def tl_capture():
    for filename in enumerate(
            camera.capture_continuous('image{counter:04d}.jpg')):
        (sched_dict, now, today) = set_time()
        print('Image recorded to {0} at {1}[UTC]'.format(filename, now))
        time.sleep(tl_interval)
        roll = check_rolling()
        if roll == False: break
    return

def check_rolling():
    (sched_dict, now, today) = set_time()
#    rolling = False
    if rec_dawn and (sched_dict['dawn'] < now < sched_dict['rec_cutoff_dawn']):
        rolling = True
        print('Recording from {0} to {1}'.format(sched_dict['dawn'], sched_dict['rec_cutoff_dawn']))
    elif rec_sunrise and (sched_dict['sunrise'] < now < sched_dict['rec_cutoff_sunrise']):
        rolling = True
        print('Recording from {0} to {1}'.format(sched_dict['sunrise'], sched_dict['rec_cutoff_sunrise']))
    elif rec_dusk and (sched_dict['dusk'] < now < sched_dict['rec_cutoff_dusk']):
        rolling = True
        print('Recording from {0} to {1}'.format(sched_dict['dusk'], sched_dict['rec_cutoff_dusk']))
    elif rec_sunset and (sched_dict['sunset'] < now < sched_dict['rec_cutoff_sunset']):
        rolling = True
        print('Recording from {0} to {1}'.format(sched_dict['sunset'], sched_dict['rec_cutoff_sunset']))
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
