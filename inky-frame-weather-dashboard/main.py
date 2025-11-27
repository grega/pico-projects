import inky_frame
import jpegdec
import json
import machine
import network
import ntptime
import os
import sdcard
import time
import urequests

from picographics import PicoGraphics, DISPLAY_INKY_FRAME_7 as DISPLAY
from time import sleep

try:
    from secrets import WIFI_SSID, WIFI_PASSWORD, LOCATION_NAME, LATITUDE, LONGITUDE, UTC_OFFSET_HOURS
except ImportError:
    print("ERROR: secrets.py not found!")
    raise

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if wlan.isconnected():
        print("Already connected to WiFi")
        return True
    
    print(f"Connecting to WiFi: {WIFI_SSID}")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    
    max_wait = 30
    while max_wait > 0:
        if wlan.isconnected():
            print(f"Connected to WiFi")
            print(f"IP: {wlan.ifconfig()[0]}")
            return True
        max_wait -= 1
        sleep(1)
        print(".", end="")
    
    print("\nFailed to connect to WiFi")
    return False

try:
    spi = machine.SPI(0, baudrate=40000000, sck=machine.Pin(18), mosi=machine.Pin(19), miso=machine.Pin(16))
    cs = machine.Pin(22)
    
    sd = sdcard.SDCard(spi, cs)
    os.mount(sd, '/sd')
    print("SD card mounted successfully at /sd")
except Exception as e:
    print(f"Failed to mount SD card: {e}")

graphics = PicoGraphics(display=DISPLAY)
jpeg = jpegdec.JPEG(graphics)

# color mappings for Spectra 6 display
WHITE = inky_frame.WHITE
BLACK = inky_frame.BLACK
YELLOW = inky_frame.GREEN
RED = inky_frame.BLUE
BLUE = inky_frame.YELLOW
GREEN = inky_frame.ORANGE

graphics.set_pen(WHITE)
graphics.clear()

if not connect_wifi():
    graphics.set_pen(BLACK)
    graphics.set_font("bitmap8")
    graphics.text("WiFi Connection Failed", 100, 200, scale=3)
    graphics.text("Check credentials in secrets.py", 100, 240, scale=2)
    graphics.update()
    print("Sleeping for 5 minutes before retry...")
    inky_frame.sleep_for(5)

def fetch_weather():
    url = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={LATITUDE}&lon={LONGITUDE}"
    headers = {"User-Agent": "InkyFrameWeather/1.0"}
    
    try:
        print(f"Fetching weather from {url}")
        response = urequests.get(url, headers=headers)
        data = response.json()
        response.close()
        return data
    except Exception as e:
        print(f"Error fetching weather: {e}")
        return None

def get_icon_filename(symbol_code):
    # keep day/night suffix for proper icon selection
    # remove polartwilight if present
    base_symbol = symbol_code.replace('_polartwilight', '')
    
    icon_map = {
        # day icons
        "clearsky_day": "wi-day-sunny",
        "fair_day": "wi-day-cloudy",
        "partlycloudy_day": "wi-day-cloudy",
        
        # night icons
        "clearsky_night": "wi-night-clear",
        "fair_night": "wi-night-alt-cloudy",
        "partlycloudy_night": "wi-night-alt-cloudy",
        
        # weather conditions (usable for day or night)
        "cloudy": "wi-cloudy",
        "fog": "wi-fog",
        "heavyrain": "wi-rain",
        "heavyrainandthunder": "wi-thunderstorm",
        "heavyrainshowers_day": "wi-day-showers",
        "heavyrainshowers_night": "wi-night-alt-showers",
        "heavysleet": "wi-sleet",
        "heavysleetandthunder": "wi-sleet",
        "heavysleetshowers_day": "wi-sleet",
        "heavysleetshowers_night": "wi-sleet",
        "heavysnow": "wi-snow",
        "heavysnowandthunder": "wi-snow",
        "heavysnowshowers_day": "wi-snow",
        "heavysnowshowers_night": "wi-snow",
        "lightrain": "wi-sprinkle",
        "lightrainandthunder": "wi-storm-showers",
        "lightrainshowers_day": "wi-day-showers",
        "lightrainshowers_night": "wi-night-alt-showers",
        "lightsleet": "wi-sleet",
        "lightsleetandthunder": "wi-sleet",
        "lightsleetshowers_day": "wi-sleet",
        "lightsleetshowers_night": "wi-sleet",
        "lightsnow": "wi-snow",
        "lightsnowandthunder": "wi-snow",
        "lightsnowshowers_day": "wi-snow",
        "lightsnowshowers_night": "wi-snow",
        "lightssleetshowersandthunder_day": "wi-sleet",
        "lightssleetshowersandthunder_night": "wi-sleet",
        "lightssnowshowersandthunder_day": "wi-snow",
        "lightssnowshowersandthunder_night": "wi-snow",
        "rain": "wi-rain",
        "rainandthunder": "wi-thunderstorm",
        "rainshowers_day": "wi-day-showers",
        "rainshowers_night": "wi-night-alt-showers",
        "sleet": "wi-sleet",
        "sleetandthunder": "wi-sleet",
        "sleetshowers_day": "wi-sleet",
        "sleetshowers_night": "wi-sleet",
        "snow": "wi-snow",
        "snowandthunder": "wi-snow",
        "snowshowers_day": "wi-snow",
        "snowshowers_night": "wi-snow",
    }
    
    icon_name = icon_map.get(base_symbol, "wi-cloud")
    return f"/sd/weather-icons/{icon_name}.jpg"

def wind_direction_to_compass(degrees):
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                  "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    index = round(degrees / 22.5) % 16
    return directions[index]

def parse_weather(data):
    if not data or 'properties' not in data:
        return None
    
    timeseries = data['properties']['timeseries']
    if not timeseries:
        return None
    
    current = timeseries[0]
    current_data = current['data']['instant']['details']
    
    current_symbol = 'cloudy'
    if 'next_1_hours' in current['data'] and 'summary' in current['data']['next_1_hours']:
        current_symbol = current['data']['next_1_hours']['summary']['symbol_code']
    elif 'next_6_hours' in current['data'] and 'summary' in current['data']['next_6_hours']:
        current_symbol = current['data']['next_6_hours']['summary']['symbol_code']
    
    time_blocks = ["00-06", "06-12", "12-18", "18-00"]
    
    from time import localtime
    current_hour = localtime()[3]
    
    if current_hour < 6:
        start_block = 0
    elif current_hour < 12:
        start_block = 1
    elif current_hour < 18:
        start_block = 2
    else:
        start_block = 3
    
    forecast_periods = []
    for block_idx in range(4):
        actual_block = (start_block + block_idx) % 4
        time_label = time_blocks[actual_block]
        
        entry_idx = min(block_idx * 6, len(timeseries) - 1)
        entry = timeseries[entry_idx]
        
        details = entry['data']['instant']['details']
        
        symbol = 'cloudy'
        if 'next_6_hours' in entry['data'] and 'summary' in entry['data']['next_6_hours']:
            symbol = entry['data']['next_6_hours']['summary']['symbol_code']
        elif 'next_1_hours' in entry['data'] and 'summary' in entry['data']['next_1_hours']:
            symbol = entry['data']['next_1_hours']['summary']['symbol_code']
        
        precip = 0
        if 'next_6_hours' in entry['data'] and 'details' in entry['data']['next_6_hours']:
            precip = entry['data']['next_6_hours']['details'].get('precipitation_amount', 0)
        elif 'next_1_hours' in entry['data'] and 'details' in entry['data']['next_1_hours']:
            precip = entry['data']['next_1_hours']['details'].get('precipitation_amount', 0)
        
        forecast_periods.append({
            "time": time_label,
            "icon": get_icon_filename(symbol),
            "temp": f"{round(details.get('air_temperature', 0))}°C",
            "precip": f"{precip} mm",
            "wind": f"{round(details.get('wind_speed', 0))} m/s"
        })
    
    return {
        "current_temp": f"{round(current_data.get('air_temperature', 0))}°C",
        "current_precip": "0 mm",
        "current_wind": f"{round(current_data.get('wind_speed', 0))} m/s",
        "current_wind_dir": wind_direction_to_compass(current_data.get('wind_from_direction', 0)),
        "current_humidity": f"{round(current_data.get('relative_humidity', 0))}%",
        "current_icon": get_icon_filename(current_symbol),
        "forecast_periods": forecast_periods
    }

def draw_icon(filename, x, y, width, height):
    try:
        jpeg.open_file(filename)
        # icons are 200x200
        if width <= 35:
            jpeg.decode(x, y, jpegdec.JPEG_SCALE_EIGHTH)
        elif width <= 60:
            jpeg.decode(x, y, jpegdec.JPEG_SCALE_QUARTER)
        elif width <= 120:
            jpeg.decode(x, y, jpegdec.JPEG_SCALE_HALF)
        else:
            jpeg.decode(x, y, jpegdec.JPEG_SCALE_FULL)
    except Exception as e:
        graphics.set_pen(RED)
        graphics.circle(x + width//2, y + height//2, min(width, height)//2)

print("Fetching weather data...")
weather_data = fetch_weather()
weather = parse_weather(weather_data)

if not weather:
    print("Failed to fetch weather data")
    graphics.set_pen(BLACK)
    graphics.set_font("bitmap8")
    graphics.text("Weather Data Failed", 150, 200, scale=3)
    graphics.text("Check your internet connection", 150, 240, scale=2)
    graphics.update()
    print("Sleeping for 10 minutes before retry...")
    inky_frame.sleep_for(10)

graphics.set_pen(BLUE)
graphics.rectangle(15, 15, 6, 50)
graphics.set_pen(BLACK)
graphics.set_font("bitmap8")
graphics.text(LOCATION_NAME, 30, 20, scale=3)

ntptime.settime()
lt = time.localtime(time.time() + UTC_OFFSET_HOURS * 3600)

day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
month_names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul",
               "Aug", "Sep", "Oct", "Nov", "Dec"]

day = lt[2]
if 10 <= day % 100 <= 20:
    suffix = "th"
else:
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")

date_str = f"{day_names[lt[6]]} {day}{suffix} {month_names[lt[1]]}"
graphics.set_pen(BLACK)
graphics.text(date_str, 580, 20, scale=3)

draw_icon(weather['current_icon'], 20, 70, 100, 100)
graphics.set_pen(RED)
graphics.text(weather['current_temp'], 140, 100, scale=9)

x_pos = 480
graphics.set_pen(BLACK)
graphics.text("Humidity", x_pos, 80, scale=2)
graphics.text(weather['current_humidity'], x_pos, 110, scale=3)

graphics.text("Precipitation", x_pos, 150, scale=2)
graphics.set_pen(BLUE)
graphics.text(weather['current_precip'], x_pos, 180, scale=3)

graphics.set_pen(BLACK)
graphics.text("Wind", 660, 80, scale=2)
graphics.text(weather['current_wind'], 660, 110, scale=3)

graphics.text("Direction", 660, 150, scale=2)
graphics.text(weather['current_wind_dir'], 660, 180, scale=3)

graphics.set_pen(BLUE)
graphics.rectangle(20, 218, 760, 3)

row_y = 240
row_height = 55
icon_size = 40

for i, period in enumerate(weather['forecast_periods']):
    if i > 0:
        graphics.set_pen(BLUE)
        graphics.line(20, row_y, 780, row_y)
    
    text_y = row_y + 17
    
    graphics.set_pen(GREEN)
    graphics.text(period["time"], 30, text_y, scale=3)
    
    icon_x = 200
    icon_y = row_y + 8
    draw_icon(period["icon"], icon_x, icon_y, icon_size, icon_size)
    
    graphics.set_pen(RED)
    graphics.text(period['temp'], 360, text_y, scale=3)
    
    graphics.set_pen(BLUE)
    graphics.text(period["precip"], 520, text_y, scale=3)
    
    graphics.set_pen(BLACK)
    graphics.text(period["wind"], 680, text_y, scale=3)
    
    row_y += row_height

print("Updating display...")
graphics.update()
print("Done!")

print("Going to sleep for 1 hour...")
inky_frame.sleep_for(60)
