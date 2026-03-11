# Enviro — Shared helper functions
# Stateless utilities used by main.py and board modules.
# ============================================================

import os
import time
import machine
from machine import RTC

def datetime_string():
  dt = RTC().datetime()
  return "{0:04d}-{1:02d}-{2:02d}T{4:02d}:{5:02d}:{6:02d}Z".format(*dt)

def datetime_file_string():
  dt = RTC().datetime()
  return "{0:04d}-{1:02d}-{2:02d}T{4:02d}_{5:02d}_{6:02d}Z".format(*dt)

def date_string():
  dt = RTC().datetime()
  return "{0:04d}-{1:02d}-{2:02d}".format(*dt)

def timestamp_to_epoch(dt_str):
  year = int(dt_str[0:4])
  month = int(dt_str[5:7])
  day = int(dt_str[8:10])
  hour = int(dt_str[11:13])
  minute = int(dt_str[14:16])
  second = int(dt_str[17:19])
  return time.mktime((year, month, day, hour, minute, second, 0, 0))

def uid():
  return "{:02x}{:02x}{:02x}{:02x}{:02x}{:02x}{:02x}{:02x}".format(*machine.unique_id())

def file_exists(path):
  try:
    return (os.stat(path)[0] & 0x4000) == 0
  except OSError:
    return False

def mkdir_safe(path):
  try:
    os.mkdir(path)
  except OSError:
    pass

def low_disk_space():
  s = os.statvfs(".")
  return (s[3] / s[2]) < 0.1

def free_space():
  s = os.statvfs(".")
  return round((s[3] / s[2]) * 100, 2)
