import time

try:
    import urequests as requests
except ImportError:
    import requests

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
        if hasattr(response, "json"):
            data = response.json()
        else:
            data = response.json()
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
    """Parse weather JSON into current + 6-hour blocks for display, aligned like the YR card."""
    if not data or 'properties' not in data:
        return None

    timeseries = data['properties']['timeseries']
    if not timeseries:
        return None

    current = timeseries[0]
    current_data = current['data']['instant']['details']

    # determine current symbol
    current_symbol = 'cloudy'
    if 'next_1_hours' in current['data'] and 'summary' in current['data']['next_1_hours']:
        current_symbol = current['data']['next_1_hours']['summary']['symbol_code']
    elif 'next_6_hours' in current['data'] and 'summary' in current['data']['next_6_hours']:
        current_symbol = current['data']['next_6_hours']['summary']['symbol_code']

    current_precip = 0
    if 'next_1_hours' in current['data'] and 'details' in current['data']['next_1_hours']:
        current_precip = current['data']['next_1_hours']['details'].get('precipitation_amount', 0)

    # current local time
    lt = time.localtime(time.time() + utc_offset_hours * 3600)
    current_hour = lt[3]
    current_minute = lt[4]

    # first block: from next full hour to end of current 6-hour segment
    first_block_start = (current_hour + 1) % 24
    first_block_end = ((current_hour // 6) + 1) * 6 % 24
    blocks = [(first_block_start, first_block_end)]

    # subsequent 6-hour blocks
    for i in range(3):
        start = (first_block_end + i * 6) % 24
        end = (start + 6) % 24
        blocks.append((start, end))

    forecast_periods = []

    for start_hr, end_hr in blocks:
        # find the timeseries entry at the start hour
        entry = None
        for e in timeseries:
            t_str = e['time'].split("T")[1]
            t_str = t_str.split("+")[0].replace("Z", "")
            hour = int(t_str.split(":")[0])
            if hour == start_hr:
                entry = e
                break
        if entry is None:
            # fallback: use first available entry
            entry = timeseries[0]

        details = entry['data']['instant']['details']

        # symbol code
        symbol = 'cloudy'
        if 'next_6_hours' in entry['data'] and 'summary' in entry['data']['next_6_hours']:
            symbol = entry['data']['next_6_hours']['summary']['symbol_code']
        elif 'next_1_hours' in entry['data'] and 'summary' in entry['data']['next_1_hours']:
            symbol = entry['data']['next_1_hours']['summary']['symbol_code']

        # precipitation
        precip = 0
        if 'next_6_hours' in entry['data'] and 'details' in entry['data']['next_6_hours']:
            precip = entry['data']['next_6_hours']['details'].get('precipitation_amount', 0)
        elif 'next_1_hours' in entry['data'] and 'details' in entry['data']['next_1_hours']:
            precip = entry['data']['next_1_hours']['details'].get('precipitation_amount', 0)

        forecast_periods.append({
            "time": f"{start_hr:02}-{end_hr:02}",
            "icon": get_icon_filename(symbol),
            "temp": f"{round(details.get('air_temperature', 0))}°C",
            "precip": f"{precip} mm",
            "wind": f"{round(details.get('wind_speed', 0))} m/s"
        })

    return {
        "current_temp": f"{round(current_data.get('air_temperature', 0))}°C",
        "current_precip": f"{current_precip} mm",
        "current_wind": f"{round(current_data.get('wind_speed', 0))} m/s",
        "current_wind_dir": wind_direction_to_compass(current_data.get('wind_from_direction', 0)),
        "current_humidity": f"{round(current_data.get('relative_humidity', 0))}%",
        "current_icon": get_icon_filename(current_symbol),
        "forecast_periods": forecast_periods
    }
