# Enviro Indoor — Board-specific sensor code
# Sensors: BME688 (temp/humidity/pressure/gas), BH1745 (RGBC light)
# ============================================================

import math
from ucollections import OrderedDict
import config

bme688 = None
bh1745 = None

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

def lux_from_rgbc(r, g, b, c):
  if g < 1:
    tmp = 0
  elif (c / g < 0.160):
    tmp = 0.202 * r + 0.766 * g
  else:
    tmp = 0.159 * r + 0.646 * g
  tmp = 0 if tmp < 0 else tmp
  integration_time = 160
  gain = 1
  return round(tmp / gain / integration_time * 160)

def colour_temperature_from_rgbc(r, g, b, c):
  if (g < 1) or (r + g + b < 1):
    return 0
  r_ratio = r / (r + g + b)
  b_ratio = b / (r + g + b)
  e = 2.71828
  ct = 0
  if c / g < 0.160:
    b_eff = min(b_ratio * 3.13, 1)
    ct = ((1 - b_eff) * 12746 * (e ** (-2.911 * r_ratio))) + (b_eff * 1637 * (e ** (4.865 * b_ratio)))
  else:
    b_eff = min(b_ratio * 10.67, 1)
    ct = ((1 - b_eff) * 16234 * (e ** (-2.781 * r_ratio))) + (b_eff * 1882 * (e ** (4.448 * b_ratio)))
  if ct > 10000:
    ct = 10000
  return round(ct)

def init_sensors(i2c):
  global bme688, bh1745
  from breakout_bme68x import BreakoutBME68X
  from breakout_bh1745 import BreakoutBH1745
  bme688 = BreakoutBME68X(i2c, address=0x77)
  bh1745 = BreakoutBH1745(i2c)
  i2c.writeto_mem(0x38, 0x44, b'\x02')  # undocumented BH1745 default fix

def read_sensors(vbus_present):
  data = bme688.read()

  temperature = round(data[0], 2)
  humidity = round(data[2], 2)

  # compensate for USB power heating
  if vbus_present:
    adjusted_temp = temperature - config.usb_power_temperature_offset
    abs_humidity = _relative_to_absolute_humidity(humidity, temperature)
    humidity = _absolute_to_relative_humidity(abs_humidity, adjusted_temp)
    temperature = adjusted_temp

  pressure = round(data[1] / 100.0, 2)
  gas_resistance = round(data[3])
  aqi = round(math.log(gas_resistance) + 0.04 * humidity, 1)

  bh1745.measurement_time_ms(160)
  r, g, b, c = bh1745.rgbc_raw()

  return OrderedDict({
    "temperature": temperature,
    "humidity": humidity,
    "pressure": pressure,
    "gas_resistance": gas_resistance,
    "aqi": aqi,
    "luminance": lux_from_rgbc(r, g, b, c),
    "color_temperature": colour_temperature_from_rgbc(r, g, b, c),
  })
