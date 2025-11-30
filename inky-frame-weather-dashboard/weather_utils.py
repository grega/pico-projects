import time

try:
    import network
except ImportError:
    # network is MicroPython-specific, not available in regular Python
    network = None

try:
    import urequests as requests
except ImportError:
    import requests

def connect_wifi(max_wait=30):
    if network is None:
        print("Error: network module not available (MicroPython only)")
        return False
    
    try:
        from secrets import WIFI_SSID, WIFI_PASSWORD
    except ImportError:
        print("Error: secrets.py not found")
        return False

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if wlan.isconnected():
        print("Already connected to WiFi")
        return True

    print(f"Connecting to WiFi: {WIFI_SSID}")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    
    while max_wait > 0:
        if wlan.isconnected():
            print("Connected to WiFi")
            print(f"IP: {wlan.ifconfig()[0]}")
            return True
        time.sleep(1)
        max_wait -= 1
        print(".", end="")
    
    print("\nFailed to connect to WiFi")
    return False

def weather_url(lat, lon):
    # used to print the URL in main.py for debugging
    return f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={lat}&lon={lon}"

def fetch_weather(lat, lon):
    url = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={lat}&lon={lon}"
    headers = {"User-Agent": "InkyFrameWeather/1.0"}

    try:
        # `requests` (Python) is a little different to `urequests` (MicroPython) 
        # for use when testing with non-MicroPython (ie. using the ascii.py script)
        response = requests.get(url, headers=headers)
        data = response.json()
        # urequests (MicroPython) requires explicit close(), requests (Python) doesn't need it
        if hasattr(response, "close"):
            response.close()
        return data
    except Exception as e:
        print(f"Error fetching weather: {e}")
        return None

def get_icon_filename(symbol_code):
    """Return the path to the icon jpg for a given symbol code."""
    base_symbol = symbol_code.replace('_polartwilight', '')

    icon_map = {
        "clearsky_day": "wi-day-sunny",
        "fair_day": "wi-day-cloudy",
        "partlycloudy_day": "wi-day-cloudy",
        "clearsky_night": "wi-night-clear",
        "fair_night": "wi-night-alt-cloudy",
        "partlycloudy_night": "wi-night-alt-cloudy",
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

def parse_weather(data, utc_offset_hours):
    # extract current weather conditions from the first timeseries entry
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

    current_precip = 0
    if 'next_1_hours' in current['data'] and 'details' in current['data']['next_1_hours']:
        current_precip = current['data']['next_1_hours']['details'].get('precipitation_amount', 0)

    # determine forecast periods: start from current/next hour, then show 4 periods
    # first period may be partial (<6 hours), subsequent periods are 6-hour blocks
    lt = time.localtime(time.time() + utc_offset_hours * 3600)
    current_hour = lt[3]
    current_minute = lt[4]
    
    current_block_start = (current_hour // 6) * 6
    current_block_end = current_block_start + 6
    if current_block_end == 24:
        current_block_end = 0
    
    is_last_hour = (current_hour % 6) == 5
    
    if is_last_hour:
        start_hour = (current_hour + 1) % 24
        if start_hour == current_block_end:
            current_block_end = (current_block_end + 6) % 24
    elif current_minute >= 50:
        start_hour = (current_hour + 1) % 24
    else:
        start_hour = current_hour

    periods = []
    if start_hour != current_block_end:
        periods.append((start_hour, current_block_end))
    
    remaining = 4 - len(periods)
    for i in range(remaining):
        block_start = (current_block_end + i * 6) % 24
        block_end = (block_start + 6) % 24
        periods.append((block_start, block_end))

    # find the timeseries entry closest to (at or before) the requested hour
    def find_entry_for_hour(hour):
        best_entry = None
        best_hour = -1
        for e in timeseries:
            t_str = e['time'].split("T")[1].split("+")[0].replace("Z", "")
            entry_hour = int(t_str.split(":")[0])
            if entry_hour == hour:
                return e
            if entry_hour < hour and entry_hour > best_hour:
                best_hour = entry_hour
                best_entry = e
        return best_entry if best_entry else timeseries[0]

    # extract forecast data for each period
    # for periods <6 hours, scale precipitation proportionally from 1h or 6h data
    forecast_periods = []
    for start_hr, end_hr in periods:
        entry = find_entry_for_hour(start_hr)
        if not entry:
            entry = timeseries[0]
        
        details = entry['data']['instant']['details']
        period_hours = (end_hr - start_hr) % 24
        if period_hours == 0:
            period_hours = 24

        symbol = 'cloudy'
        if period_hours >= 6 and 'next_6_hours' in entry['data'] and 'summary' in entry['data']['next_6_hours']:
            symbol = entry['data']['next_6_hours']['summary']['symbol_code']
        elif 'next_1_hours' in entry['data'] and 'summary' in entry['data']['next_1_hours']:
            symbol = entry['data']['next_1_hours']['summary']['symbol_code']
        elif 'next_6_hours' in entry['data'] and 'summary' in entry['data']['next_6_hours']:
            symbol = entry['data']['next_6_hours']['summary']['symbol_code']

        precip = 0
        if period_hours >= 6 and 'next_6_hours' in entry['data'] and 'details' in entry['data']['next_6_hours']:
            precip = entry['data']['next_6_hours']['details'].get('precipitation_amount', 0)
        elif 'next_1_hours' in entry['data'] and 'details' in entry['data']['next_1_hours']:
            precip_1h = entry['data']['next_1_hours']['details'].get('precipitation_amount', 0)
            precip = precip_1h * period_hours
        elif 'next_6_hours' in entry['data'] and 'details' in entry['data']['next_6_hours']:
            precip_6h = entry['data']['next_6_hours']['details'].get('precipitation_amount', 0)
            precip = (precip_6h / 6) * period_hours

        forecast_periods.append({
            "time": f"{start_hr:02}-{end_hr:02}",
            "icon": get_icon_filename(symbol),
            "temp": f"{round(details.get('air_temperature', 0))}°C",
            "precip": f"{precip:.1f} mm",
            "wind": f"{round(details.get('wind_speed', 0))} m/s"
        })

    return {
        "current_temp": f"{round(current_data.get('air_temperature', 0))}°C",
        "current_precip": f"{current_precip} mm",
        "current_wind": f"{round(current_data.get('wind_speed', 0))} m/s",
        "current_wind_dir": wind_direction_to_compass(current_data.get('wind_from_direction', 0)),
        "current_humidity": f"{round(current_data.get('relative_humidity', 0))}%",
        "current_cloud": f"{round(current_data.get('cloud_area_fraction', 0))}%",
        "current_pressure": f"{round(current_data.get('air_pressure_at_sea_level', 0))} hPa",
        "current_icon": get_icon_filename(current_symbol),
        "forecast_periods": forecast_periods
    }

