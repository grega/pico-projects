# logic for updating specified files from GitHub with rollback on failure

import os
import time
import urequests

# local imports
from secrets import WIFI_SSID, WIFI_PASSWORD
from weather_utils import connect_wifi

GITHUB_BASE_URL = "https://raw.githubusercontent.com/grega/pico-projects/main/inky-frame-weather-dashboard/"
FILES_TO_UPDATE = ["main.py", "weather_utils.py"]
BOOT_COUNTER_FILE = "boot_counter.txt"
MAX_RETRIES = 3
STABLE_VALUE = 10 # arbirtrary, just needs to be > MAX_RETRIES (stops boot counter from incrementing forever)
CHECK_INTERVAL = 3600 # seconds between automatic checks

def read_boot_counter():
    try:
        with open(BOOT_COUNTER_FILE, "r") as f:
            return int(f.read())
    except Exception:
        return 0

def write_boot_counter(value):
    with open(BOOT_COUNTER_FILE, "w") as f:
        f.write(str(value))

def mark_boot_success():
    counter = read_boot_counter()
    if counter < STABLE_VALUE:
        counter += 1
        write_boot_counter(counter)

def mark_boot_failure():
    counter = read_boot_counter()
    counter += 1
    write_boot_counter(counter)

def rollback_if_needed():
    counter = read_boot_counter()
    if counter > MAX_RETRIES:
        for file in FILES_TO_UPDATE:
            prev_file = file + ".prev"
            if prev_file in os.listdir():
                os.rename(file, file + ".bad")
                os.rename(prev_file, file)
                print(f"Rollback performed for {file}")
        write_boot_counter(0)

def fetch_file(file):
    url = GITHUB_BASE_URL + file
    headers = {"User-Agent": "PicoUpdater/1.0"}
    try:
        response = urequests.get(url, headers=headers)
        content = response.text
        # save current version as backup
        if file in os.listdir():
            os.rename(file, file + ".prev")
        with open(file, "w") as f:
            f.write(content)
        print(f"Updated {file} from GitHub")
    except Exception as e:
        print(f"Error fetching {file}: {e}")
        mark_boot_failure()
        rollback_if_needed()

def update_all():
  if connect_wifi():
      print("WiFi ready")
      for file in FILES_TO_UPDATE:
        fetch_file(file)
        mark_boot_success()
  else:
      print("Cannot connect to WiFi")
