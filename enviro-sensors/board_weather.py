# Enviro Weather — Board-specific sensor code
# Sensors: BME280 (temp/humidity/pressure), LTR-559 (lux),
#          wind vane (analog), anemometer (pulse), rain gauge (tipping bucket)
# ============================================================

import math
import time
import os
from machine import Pin
from time import sleep
from ucollections import OrderedDict
import config
import logging
import helpers

WIND_SPEED_PIN = 9
RAIN_PIN = 10
WIND_DIRECTION_PIN = 26

RAIN_MM_PER_TICK = 0.2794
WIND_CM_RADIUS = 7.0
WIND_FACTOR = 0.0218

bme280 = None
ltr559 = None
_LTR559_LUX = None
wind_direction_pin = None
wind_speed_pin = None
rain_pin = None
_last_rain_state = False

def init_sensors(i2c):
  global bme280, ltr559, _LTR559_LUX, wind_direction_pin, wind_speed_pin, rain_pin
  from breakout_bme280 import BreakoutBME280
  from breakout_ltr559 import BreakoutLTR559
  from pimoroni import Analog
  bme280 = BreakoutBME280(i2c, 0x77)
  ltr559 = BreakoutLTR559(i2c)
  _LTR559_LUX = BreakoutLTR559.LUX
  wind_direction_pin = Analog(WIND_DIRECTION_PIN)
  wind_speed_pin = Pin(WIND_SPEED_PIN, Pin.IN, Pin.PULL_UP)
  rain_pin = Pin(RAIN_PIN, Pin.IN, Pin.PULL_DOWN)

def measure_wind_speed(sample_time_ms=1000):
  """Sample anemometer pulses and return wind speed in m/s."""
  state = wind_speed_pin.value()
  ticks = []

  start = time.ticks_ms()
  while time.ticks_diff(time.ticks_ms(), start) <= sample_time_ms:
    now = wind_speed_pin.value()
    if now != state:
      ticks.append(time.ticks_ms())
      state = now

  if len(ticks) < 2:
    return 0

  average_tick_ms = time.ticks_diff(ticks[-1], ticks[0]) / (len(ticks) - 1)
  if average_tick_ms == 0:
    return 0

  rotation_hz = (1000 / average_tick_ms) / 2
  circumference = WIND_CM_RADIUS * 2.0 * math.pi
  return rotation_hz * circumference * WIND_FACTOR

def measure_wind_direction():
  """Read wind vane ADC and return compass heading in degrees (0-315, 45 deg steps)."""
  ADC_TO_DEGREES = (0.9, 2.0, 3.0, 2.8, 2.5, 1.5, 0.3, 0.6)

  last_index = None
  while True:
    value = wind_direction_pin.read_voltage()
    closest_index = -1
    closest_value = float('inf')
    for i in range(8):
      distance = abs(ADC_TO_DEGREES[i] - value)
      if distance < closest_value:
        closest_value = distance
        closest_index = i
    if last_index == closest_index:
      break
    last_index = closest_index

  return closest_index * 45

def _record_rain_tip():
  rain_entries = []
  if helpers.file_exists("rain.txt"):
    with open("rain.txt", "r") as f:
      rain_entries = f.read().split("\n")
  rain_entries.append(helpers.datetime_string())
  # keep at most 190 entries (~4KB, fits in one filesystem block)
  rain_entries = rain_entries[-190:]
  with open("rain.txt", "w") as f:
    f.write("\n".join(rain_entries))

def pre_read():
  """Poll the rain pin and record a tip if detected."""
  global _last_rain_state
  current = rain_pin.value()
  if current and not _last_rain_state:
    _record_rain_tip()
    logging.debug("> rain tip recorded")
  _last_rain_state = current

def _rainfall_since(seconds_since_last):
  """Calculate rainfall (mm) and rain rate (mm/s) from rain.txt entries."""
  amount = 0
  now = helpers.timestamp_to_epoch(helpers.datetime_string())
  if helpers.file_exists("rain.txt"):
    with open("rain.txt", "r") as f:
      rain_entries = f.read().split("\n")
    for entry in rain_entries:
      if entry:
        ts = helpers.timestamp_to_epoch(entry)
        if now - ts < seconds_since_last:
          amount += RAIN_MM_PER_TICK
    os.remove("rain.txt")

  per_second = amount / seconds_since_last if seconds_since_last > 0 else 0
  return amount, per_second

def read_sensors(vbus_present):
  # BME280 returns stale register contents on first read; do a dummy
  # read, wait briefly, then read the fresh measurement.
  bme280.read()
  time.sleep(0.1)
  bme280_data = bme280.read()

  ltr_data = ltr559.get_reading()

  # use reading_frequency (minutes) as the rain accumulation window
  seconds_since_last = config.reading_frequency * 60
  rain, rain_per_second = _rainfall_since(seconds_since_last)

  return OrderedDict({
    "temperature": round(bme280_data[0], 2),
    "humidity": round(bme280_data[2], 2),
    "pressure": round(bme280_data[1] / 100.0, 2),
    "luminance": round(ltr_data[_LTR559_LUX], 2),
    "wind_speed": round(measure_wind_speed(), 2),
    "rain": round(rain, 4),
    "rain_per_second": round(rain_per_second, 4),
    "wind_direction": measure_wind_direction(),
  })
