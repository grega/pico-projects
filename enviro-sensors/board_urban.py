# Enviro Urban — Board-specific sensor code
# Sensors: BME280 (temp/humidity/pressure), PMS5003I (particulate matter),
#          MEMS microphone (noise level)
# ============================================================

import math
import time
from machine import Pin, ADC
from time import sleep
from ucollections import OrderedDict
import config
import logging

SENSOR_RESET_PIN = 9
SENSOR_ENABLE_PIN = 10
BOOST_ENABLE_PIN = 11
PMS_I2C_SDA_PIN = 14
PMS_I2C_SCL_PIN = 15
NOISE_ADC_PIN = 0
MIC_SAMPLE_TIME_MS = 3000

# PMS5003I data frame field indices
PM1_UGM3 = 2
PM2_5_UGM3 = 3
PM10_UGM3 = 4

bme280 = None
sensor_reset_pin = None
sensor_enable_pin = None
boost_enable_pin = None
noise_adc = None

# humidity conversion helpers (for USB temperature compensation)
WATER_VAPOR_SPECIFIC_GAS_CONSTANT = 461.5
CRITICAL_WATER_TEMPERATURE = 647.096
CRITICAL_WATER_PRESSURE = 22064000

def _celcius_to_kelvin(t):
  return t + 273.15

def _saturation_vapor_pressure(temp_k):
  v = 1 - (temp_k / CRITICAL_WATER_TEMPERATURE)
  a1, a2, a3, a4, a5, a6 = -7.85951783, 1.84408259, -11.7866497, 22.6807411, -15.9618719, 1.80122502
  return CRITICAL_WATER_PRESSURE * math.exp(
    CRITICAL_WATER_TEMPERATURE / temp_k *
    (a1*v + a2*v**1.5 + a3*v**3 + a4*v**3.5 + a5*v**4 + a6*v**7.5)
  )

def _relative_to_absolute_humidity(rh, temp_c):
  temp_k = _celcius_to_kelvin(temp_c)
  actual_vp = _saturation_vapor_pressure(temp_k) * (rh / 100)
  return actual_vp / (WATER_VAPOR_SPECIFIC_GAS_CONSTANT * temp_k)

def _absolute_to_relative_humidity(ah, temp_c):
  temp_k = _celcius_to_kelvin(temp_c)
  svp = _saturation_vapor_pressure(temp_k)
  return (WATER_VAPOR_SPECIFIC_GAS_CONSTANT * temp_k * ah) / svp * 100

def particulates(data, measure):
  """Decode a 16-bit big-endian value from the PMS5003I data frame."""
  return (data[measure * 2] << 8) | data[measure * 2 + 1]

def init_sensors(i2c):
  global bme280, sensor_reset_pin, sensor_enable_pin, boost_enable_pin, noise_adc
  from breakout_bme280 import BreakoutBME280
  bme280 = BreakoutBME280(i2c, 0x77)
  sensor_reset_pin = Pin(SENSOR_RESET_PIN, Pin.OUT, value=True)
  sensor_enable_pin = Pin(SENSOR_ENABLE_PIN, Pin.OUT, value=False)
  boost_enable_pin = Pin(BOOST_ENABLE_PIN, Pin.OUT, value=False)
  noise_adc = ADC(NOISE_ADC_PIN)

def read_sensors(vbus_present):
  # BME280 returns stale register contents on first read; do a dummy read,
  # wait briefly, then read again for a fresh result.
  bme280.read()
  sleep(0.1)
  bme280_data = bme280.read()

  temperature = round(bme280_data[0], 2)
  humidity = round(bme280_data[2], 2)

  # compensate for USB power heating
  if vbus_present:
    adjusted_temp = temperature - config.usb_power_temperature_offset
    abs_humidity = _relative_to_absolute_humidity(humidity, temperature)
    humidity = _absolute_to_relative_humidity(abs_humidity, adjusted_temp)
    temperature = adjusted_temp

  pressure = round(bme280_data[1] / 100.0, 2)

  # ---- particulate matter sensor (PMS5003I) ----
  logging.debug("  - powering up PMS5003")
  boost_enable_pin.value(True)
  sensor_enable_pin.value(True)
  sleep(5)  # allow airflow to stabilise

  logging.debug("  - reading PMS5003I via I2C")
  from pimoroni_i2c import PimoroniI2C
  pms_i2c = PimoroniI2C(PMS_I2C_SDA_PIN, PMS_I2C_SCL_PIN, 100000)
  particulate_data = pms_i2c.readfrom_mem(0x12, 0x00, 32)

  sensor_enable_pin.value(False)
  boost_enable_pin.value(False)

  # ---- microphone (noise level as peak-to-peak voltage) ----
  logging.debug("  - sampling microphone")
  start = time.ticks_ms()
  min_value = 1.65
  max_value = 1.65
  while time.ticks_diff(time.ticks_ms(), start) < MIC_SAMPLE_TIME_MS:
    value = (noise_adc.read_u16() * 3.3) / 65535
    min_value = min(min_value, value)
    max_value = max(max_value, value)
  noise_vpp = max_value - min_value

  return OrderedDict({
    "temperature": temperature,
    "humidity": humidity,
    "pressure": pressure,
    "noise": round(noise_vpp, 3),
    "pm1": particulates(particulate_data, PM1_UGM3),
    "pm2_5": particulates(particulate_data, PM2_5_UGM3),
    "pm10": particulates(particulate_data, PM10_UGM3),
  })
