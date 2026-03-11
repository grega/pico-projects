# Enviro — Custom Firmware (Unified)
# Standalone replacement for Pimoroni's enviro library.
# Supports Indoor, Weather, and Urban boards via config.model.
# Requires Pimoroni's custom MicroPython UF2 for sensor drivers.
# ============================================================

# latch power rail immediately — on battery wake the hold capacitor
# drains in ~hundreds of ms, so this must happen before anything else.
from machine import Pin, PWM, RTC, ADC
hold_vsys_en_pin = Pin(2, Pin.OUT, value=True)

from time import sleep
sleep(0.5)  # Issue #117: short delay on startup to ensure stable boot

import gc
import math
import os
import machine
import time
import ujson
import struct
import usocket

from ucollections import OrderedDict

import config
import logging
import helpers

# ============================================================
# Hardware constants (common to all boards)
# ============================================================
HOLD_VSYS_EN_PIN = 2
I2C_SDA_PIN = 4
I2C_SCL_PIN = 5
ACTIVITY_LED_PIN = 6
BUTTON_PIN = 7
RTC_ALARM_PIN = 8
WIFI_CS_PIN = 25

# ============================================================
# Hardware init
# ============================================================

# detect USB power
_vbus_pin = Pin("WL_GPIO2", Pin.IN)
vbus_present = _vbus_pin.value()

# reset I2C bus — after an unclean reset (e.g. USB disconnect) the bus
# can be stuck mid-transaction. toggling SCL while SDA is released
# sends enough clocks to unstick any peripheral.
_sda_reset = Pin(I2C_SDA_PIN, Pin.IN, Pin.PULL_UP)
_scl_reset = Pin(I2C_SCL_PIN, Pin.OUT, value=1)
for _ in range(16):
  _scl_reset.value(0)
  sleep(0.001)
  _scl_reset.value(1)
  sleep(0.001)
_sda_reset.init(Pin.IN)
_scl_reset.init(Pin.IN)
sleep(0.01)

# I2C bus
from pimoroni_i2c import PimoroniI2C
i2c = PimoroniI2C(I2C_SDA_PIN, I2C_SCL_PIN, 100000)

# RTC (PCF85063A)
from pcf85063a import PCF85063A
rtc = PCF85063A(i2c)
i2c.writeto_mem(0x51, 0x00, b'\x00')  # ensure RTC is running
rtc.enable_timer_interrupt(False)

# sync Pico's internal RTC from external RTC
t = rtc.datetime()
RTC().datetime((t[0], t[1], t[2], t[6], t[3], t[4], t[5], 0))

# turn off warning LED (RTC clock output defaults to 32KHz)
rtc.set_clock_output(PCF85063A.CLOCK_OUT_OFF)

# ============================================================
# Board-specific sensor init
# ============================================================
board = __import__("board_" + config.model)
board.init_sensors(i2c)

# activity LED — simple on/off
activity_led_pwm = PWM(Pin(ACTIVITY_LED_PIN))
activity_led_pwm.freq(1000)
activity_led_pwm.duty_u16(0)

# button
button_pin = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_DOWN)

# ============================================================
# Helper functions
# ============================================================

def led_on():
  if not config.silent_mode:
    activity_led_pwm.duty_u16(32768)

def led_off():
  activity_led_pwm.duty_u16(0)

def warn_led_blink():
  if not config.silent_mode:
    rtc.set_clock_output(PCF85063A.CLOCK_OUT_1HZ)

def warn_led_off():
  rtc.set_clock_output(PCF85063A.CLOCK_OUT_OFF)

# ============================================================
# WiFi
# ============================================================

def connect_wifi():
  import network
  import rp2

  rp2.country(config.wifi_country)
  wlan = network.WLAN(network.STA_IF)

  if vbus_present:
    wlan.config(pm=0xa11140)  # disable power saving on USB

  wlan.active(True)

  # disconnect if in a stale state
  if wlan.status() >= 1 and wlan.status() < 3:
    wlan.disconnect()
    for _ in range(20):
      sleep(0.5)
      if wlan.status() <= 0:
        break

  logging.info(f"> connecting to wifi '{config.wifi_ssid}'")
  wlan.connect(config.wifi_ssid, config.wifi_password)

  for _ in range(20):  # 10 second timeout
    sleep(0.5)
    status = wlan.status()
    if status == 3:  # CYW43_LINK_UP
      ip = wlan.ifconfig()[0]
      logging.info(f"> wifi connected, IP: {ip}")
      return True
    if status < 0:  # error state
      logging.error(f"> wifi failed, status: {status}")
      return False

  logging.error("> wifi connection timed out")
  return False

def disconnect_wifi():
  import network
  try:
    wlan = network.WLAN(network.STA_IF)
    wlan.disconnect()
    wlan.active(False)
    logging.info("> wifi disconnected")
  except:
    pass

# ============================================================
# NTP time sync
# ============================================================

def ntp_fetch():
  """Fetch time from NTP server. Returns time tuple or None."""
  try:
    query = bytearray(48)
    query[0] = 0x1b
    addr = usocket.getaddrinfo("pool.ntp.org", 123)[0][-1]
    sock = usocket.socket(usocket.AF_INET, usocket.SOCK_DGRAM)
    sock.settimeout(10)
    sock.sendto(query, addr)
    data = sock.recv(48)
    sock.close()
    ntp_epoch_offset = 2208988800
    ts = struct.unpack("!I", data[40:44])[0] - ntp_epoch_offset
    return time.gmtime(ts)
  except Exception as e:
    logging.error(f"> NTP fetch failed: {e}")
    return None

def sync_clock_from_ntp():
  """Connect WiFi, fetch NTP time, write to external RTC. Returns True on success."""
  if not connect_wifi():
    return False

  ts = ntp_fetch()
  disconnect_wifi()

  if not ts:
    return False

  # stop RTC, set time, restart
  i2c.writeto_mem(0x51, 0x00, b'\x10')
  rtc.datetime(ts)
  i2c.writeto_mem(0x51, 0x00, b'\x00')
  rtc.enable_timer_interrupt(False)

  # verify
  dt = rtc.datetime()
  if dt != ts[0:7]:
    logging.error("> failed to set RTC time")
    if helpers.file_exists("sync_time.txt"):
      os.remove("sync_time.txt")
    return False

  # sync Pico internal RTC too
  RTC().datetime((ts[0], ts[1], ts[2], ts[6], ts[3], ts[4], ts[5], 0))

  # record sync time
  with open("sync_time.txt", "w") as f:
    f.write("{0:04d}-{1:02d}-{2:02d}T{3:02d}:{4:02d}:{5:02d}Z".format(*ts))

  logging.info("> RTC synced via NTP")
  return True

def is_clock_set():
  """Returns True if RTC has a valid recent time and NTP sync is fresh."""
  if rtc.datetime()[0] <= 2020:
    return False

  if helpers.file_exists("sync_time.txt"):
    now = helpers.timestamp_to_epoch(helpers.datetime_string())
    with open("sync_time.txt", "r") as f:
      sync_str = f.read().strip()
    if sync_str:
      sync = helpers.timestamp_to_epoch(sync_str)
      age_seconds = now - sync
      if age_seconds >= 0 and age_seconds < (config.resync_frequency * 3600):
        return True
      logging.info(f"> NTP sync is {age_seconds}s old, needs refresh")

  return False

# ============================================================
# Local CSV storage
# ============================================================

def save_reading_locally(readings):
  helpers.mkdir_safe("readings")

  # write column headings once
  if not helpers.file_exists("readings/columns.txt"):
    with open("readings/columns.txt", "w") as f:
      f.write("timestamp," + ",".join(readings.keys()) + "\n")

  filename = f"readings/{helpers.date_string()}.csv"
  with open(filename, "a") as f:
    row = [helpers.datetime_string()]
    for key in readings.keys():
      row.append(str(readings[key]))
    f.write(",".join(row) + "\n")

# ============================================================
# Upload cache and HTTP POST
# ============================================================

def cache_reading(readings):
  """Save reading as JSON for later upload."""
  payload = {
    "nickname": config.nickname,
    "timestamp": helpers.datetime_string(),
    "readings": readings,
    "model": config.model,
    "uid": helpers.uid(),
    "power_mode": "usb" if vbus_present else "batt",
    "free_space": helpers.free_space(),
  }
  helpers.mkdir_safe("uploads")
  filename = f"uploads/{helpers.datetime_file_string()}.json"
  with open(filename, "w") as f:
    f.write(ujson.dumps(payload))

def cached_upload_count():
  try:
    return len(os.listdir("uploads"))
  except OSError:
    return 0

def upload_cached_readings():
  """Upload all cached JSON files. Returns True if all succeeded."""
  count = cached_upload_count()
  if count == 0:
    return True

  if not connect_wifi():
    logging.error("> cannot upload, wifi failed")
    return False

  import urequests

  logging.info(f"> uploading {count} cached reading(s) to {config.upload_url}")

  all_ok = True
  try:
    files = sorted(os.listdir("uploads"))
    for fname in files:
      fpath = f"uploads/{fname}"
      try:
        with open(fpath, "r") as f:
          payload = ujson.load(f)

        auth = None
        if config.http_username:
          auth = (config.http_username, config.http_password)

        result = urequests.post(config.upload_url, auth=auth, json=payload)
        status = result.status_code
        result.close()

        if status in (200, 201, 202):
          os.remove(fpath)
          logging.info(f"  - uploaded {fname}")
        else:
          logging.error(f"  - upload failed for {fname} (HTTP {status})")
          all_ok = False
          break  # stop on first failure, retry next cycle

      except Exception as e:
        logging.error(f"  - upload error for {fname}: {e}")
        all_ok = False
        break

  finally:
    disconnect_wifi()

  return all_ok

# ============================================================
# Sleep / wait for next reading
# ============================================================

def calculate_next_reading():
  """Returns (hour, minute, wait_seconds) for the next aligned reading time."""
  dt = rtc.datetime()
  hour, minute, second = dt[3:6]

  if second > 55:
    minute += 1

  minute = math.floor(minute / config.reading_frequency) * config.reading_frequency
  minute += config.reading_frequency

  while minute >= 60:
    minute -= 60
    hour += 1
  if hour >= 24:
    hour -= 24

  now_seconds = dt[3] * 3600 + dt[4] * 60 + dt[5]
  alarm_seconds = hour * 3600 + minute * 60
  wait_seconds = alarm_seconds - now_seconds
  if wait_seconds <= 0:
    wait_seconds += 86400

  return hour, minute, wait_seconds

def do_sleep():
  """Sleep until next reading. On battery: RTC alarm + power off. On USB: time.sleep()."""
  hour, minute, wait_seconds = calculate_next_reading()
  ampm = "am" if hour < 12 else "pm"

  os.sync()
  gc.collect()
  led_off()

  if not vbus_present:
    # battery path: set RTC alarm and power off
    logging.info(f"> alarm set for {hour:02}:{minute:02}{ampm}, powering off")
    rtc.clear_timer_flag()
    rtc.clear_alarm_flag()
    rtc.set_alarm(0, minute, hour)
    rtc.enable_alarm_interrupt(True)
    hold_vsys_en_pin.init(Pin.IN)  # release power rail → board powers off
    # if still alive, something is wrong — wait and reset
    sleep(5)
    machine.reset()
  else:
    # USB path: simple sleep, no I2C polling, no machine.reset()
    logging.info(f"> sleeping {wait_seconds}s until {hour:02}:{minute:02}{ampm}")
    sleep(wait_seconds)
    logging.info("> waking up")

# ============================================================
# Main loop
# ============================================================

logging.info(f"> enviro {config.model} custom firmware starting")
logging.info(f"> uid: {helpers.uid()}, usb: {vbus_present}")

consecutive_errors = 0
MAX_CONSECUTIVE_ERRORS = 3  # flash red LED after this many failures in a row

while True:
  try:
    gc.collect()
    led_on()

    # ---- re-check power source each cycle ----
    vbus_present = _vbus_pin.value()

    # ---- clock sync ----
    if not is_clock_set():
      logging.info("> clock not set or stale, syncing via NTP")
      if not sync_clock_from_ntp():
        logging.error("> NTP sync failed, retrying in 60s")
        led_off()
        sleep(60)
        continue

    # ---- retry pending uploads ----
    if helpers.file_exists("reattempt_upload.txt"):
      logging.info(f"> retrying {cached_upload_count()} pending upload(s)")
      if upload_cached_readings():
        os.remove("reattempt_upload.txt")
        logging.info("> retry upload successful")
      else:
        logging.error("> retry upload failed, will try again next cycle")

    # ---- disk space check ----
    if helpers.low_disk_space():
      logging.error("> low disk space, attempting upload to free cache")
      if upload_cached_readings():
        # uploads freed space, clear retry sentinel if present
        if helpers.file_exists("reattempt_upload.txt"):
          os.remove("reattempt_upload.txt")
      else:
        # uploads failed too — thin out cached JSON files to free space
        # removes every other file, halving the cache while preserving
        # coverage across the full time range (reduced resolution, not data loss)
        logging.error("> upload failed and disk is low, thinning cache")
        try:
          files = sorted(os.listdir("uploads"))
          to_remove = [f for i, f in enumerate(files) if i % 2 == 1]
          for fname in to_remove:
            os.remove(f"uploads/{fname}")
          logging.info(f"> thinned {len(to_remove)} of {len(files)} cached upload(s)")
        except OSError as e:
          logging.error(f"> cache thinning failed: {e}")

    # ---- board-specific pre-read (e.g. rain trigger check for weather) ----
    if hasattr(board, 'pre_read'):
      board.pre_read()

    # ---- read sensors ----
    reading = board.read_sensors(vbus_present)
    logging.info("> reading taken")

    # ---- storage info ----
    stats = os.statvfs(".")
    free_kb = (stats[0] * stats[3]) // 1024
    total_kb = (stats[0] * stats[2]) // 1024
    logging.info(f"> storage: {free_kb}KB free / {total_kb}KB total")

    # ---- save locally ----
    try:
      save_reading_locally(reading)
      logging.debug("> saved reading to CSV")
    except Exception as e:
      logging.error(f"> CSV save failed: {e}")

    # ---- cache for upload ----
    cache_reading(reading)
    count = cached_upload_count()

    # ---- upload if threshold reached ----
    if count >= config.upload_frequency:
      logging.info(f"> {count} cached, uploading")
      if not upload_cached_readings():
        # mark for retry next cycle
        with open("reattempt_upload.txt", "w") as f:
          f.write("")
        logging.error("> upload failed, marked for retry")
    else:
      logging.info(f"> {count} cached, waiting for {config.upload_frequency}")

    # ---- success: reset error counter and clear warning LED ----
    consecutive_errors = 0
    warn_led_off()

    # ---- sleep ----
    do_sleep()

  except Exception as exc:
    import sys, io
    buf = io.StringIO()
    sys.print_exception(exc, buf)
    logging.error(f"> exception: {buf.getvalue()}")
    led_off()
    consecutive_errors += 1

    # determine if a reboot would likely fix this
    reboot_worthy = (
      isinstance(exc, MemoryError)
      or isinstance(exc, OSError)  # I2C / hardware failures
      or consecutive_errors >= MAX_CONSECUTIVE_ERRORS
    )

    exc_name = type(exc).__name__
    if reboot_worthy:
      warn_led_blink()  # flash red LED until user reboots
      logging.error(f"> reboot recommended ({consecutive_errors} error(s), type: {exc_name})")
    else:
      logging.info(f"> transient error ({consecutive_errors}/{MAX_CONSECUTIVE_ERRORS}), retrying in 60s")

    sleep(60)
