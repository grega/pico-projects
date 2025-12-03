import os
import time
import urequests

from secrets import WIFI_SSID, WIFI_PASSWORD
try:
    from secrets import ENABLE_AUTO_UPDATE
except ImportError:
    ENABLE_AUTO_UPDATE = False
from weather_utils import connect_wifi

GITHUB_BASE_URL = "https://raw.githubusercontent.com/grega/pico-projects/main/inky-frame-weather-dashboard/"
FILES_TO_UPDATE = ["app.py", "weather_utils.py"]
FAILURE_COUNT_FILE = "failure_count.txt"

def read_failure_count():
    try:
        with open(FAILURE_COUNT_FILE, "r") as f:
            return int(f.read())
    except Exception:
        return 0

def write_failure_count(count):
    with open(FAILURE_COUNT_FILE, "w") as f:
        f.write(str(count))

def mark_boot_success():
    write_failure_count(0)

def mark_boot_failure():
    count = read_failure_count()
    write_failure_count(count + 1)

def fetch_file(file):
    url = GITHUB_BASE_URL + file
    headers = {"User-Agent": "PicoUpdater/1.0"}

    try:
        print(f"Fetching {url}")
        response = urequests.get(url, headers=headers)
        content = response.text
        response.close()

        if file in os.listdir():
            with open(file, "r") as f:
                existing_content = f.read()
            if existing_content == content:
                print(f"No changes for {file}")
                return True

            prev_file = file + ".prev"
            if prev_file in os.listdir():
                os.remove(prev_file)
            os.rename(file, prev_file)
        with open(file, "w") as f:
            f.write(content)

        print(f"Updated {file} from GitHub")
        return True

    except Exception as e:
        print(f"Error fetching {file}: {e}")
        return False

def update_all():
    if not ENABLE_AUTO_UPDATE:
        print("Auto-update is disabled (ENABLE_AUTO_UPDATE = False)")
        return True
    
    if not connect_wifi():
        print("Cannot connect to WiFi")
        return False
    
    print("WiFi ready")
    all_succeeded = True
    
    for file in FILES_TO_UPDATE:
        if not fetch_file(file):
            all_succeeded = False
    
    return all_succeeded
