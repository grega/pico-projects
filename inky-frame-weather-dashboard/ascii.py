#!/usr/bin/env python3
"""ASCII renderer for the parsed weather dict.

Exposes `render_ascii(weather, location_name, utc_offset_hours)` for reuse by
main.py (served at /ascii). Running this file directly fetches live data and
prints it - handy for local development without a device.
"""

import time


def render_ascii(weather, location_name, utc_offset_hours=0):
    lt = time.localtime(time.time() + utc_offset_hours * 3600)
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    month_names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul",
                   "Aug", "Sep", "Oct", "Nov", "Dec"]
    day = lt[2]
    if 10 <= day % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    date_str = f"{day_names[lt[6]]} {day}{suffix} {month_names[lt[1]]}"

    lines = []
    lines.append("=" * 80)
    lines.append(f"Weather for {location_name}")
    lines.append(date_str)
    lines.append("-" * 80)

    if not weather:
        lines.append("No weather data available yet.")
        lines.append("=" * 80)
        return "\n".join(lines)

    current_icon = weather["current_icon"].split("/")[-1]
    lines.append(f"Temperature:         {weather['current_temp']}")
    lines.append(f"Icon:                {current_icon}")
    lines.append("")
    lines.append(f"Cloud:               {weather['current_cloud']}")
    lines.append(f"Pressure:            {weather['current_pressure']}")
    lines.append(f"Humidity:            {weather['current_humidity']}")
    lines.append(f"Precipitation:       {weather['current_precip']}")
    lines.append(f"Wind:                {weather['current_wind']}")
    lines.append(f"Direction:           {weather['current_wind_dir']}")
    lines.append("-" * 80)
    lines.append(f"{'Time':<10} {'Temp':<7} {'Icon':<25} {'Precip':<8} {'Wind'}")
    lines.append("-" * 80)
    for period in weather["forecast_periods"]:
        icon = period["icon"].split("/")[-1]
        lines.append(f"{period['time']:<10} {period['temp']:<7} {icon:<25} {period['precip']:<8} {period['wind']}")
    lines.append("=" * 80)
    return "\n".join(lines)


def display_ascii():
    """CLI entry point: fetch live weather and print to stdout."""
    from weather_utils import fetch_weather, parse_weather
    from config import LOCATION_NAME, LATITUDE, LONGITUDE, UTC_OFFSET_HOURS

    data = fetch_weather(LATITUDE, LONGITUDE)
    weather = parse_weather(data, UTC_OFFSET_HOURS)
    if not weather:
        print("Failed to fetch weather data")
        return
    print(render_ascii(weather, LOCATION_NAME, UTC_OFFSET_HOURS))


if __name__ == "__main__":
    display_ascii()
