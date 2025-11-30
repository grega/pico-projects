#!/usr/bin/env python3
from weather_utils import fetch_weather, parse_weather
from secrets import LOCATION_NAME, LATITUDE, LONGITUDE, UTC_OFFSET_HOURS

def display_ascii():
    print("="*80)
    print(f"Weather for {LOCATION_NAME}")
    
    from time import localtime
    lt = localtime()
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    month_names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul",
                   "Aug", "Sep", "Oct", "Nov", "Dec"]
    day = lt[2]
    if 10 <= day % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    date_str = f"{day_names[lt[6]]} {day}{suffix} {month_names[lt[1]]}"
    print(date_str)
    print("-"*80)

    # fetch and parse weather
    data = fetch_weather(LATITUDE, LONGITUDE)
    weather = parse_weather(data, UTC_OFFSET_HOURS)
    if not weather:
        print("Failed to fetch weather data")
        return

    # current weather (matches Inky Frame layout: left to right, top to bottom)
    print(f"Temperature:         {weather['current_temp']}")
    current_icon_name = weather['current_icon'].split("/")[-1]
    print(f"Icon:                {current_icon_name}")
    print()
    print(f"Cloud:               {weather['current_cloud']}")
    print(f"Pressure:            {weather['current_pressure']}")
    print(f"Humidity:            {weather['current_humidity']}")
    print(f"Precipitation:       {weather['current_precip']}")
    print(f"Wind:                {weather['current_wind']}")
    print(f"Direction:           {weather['current_wind_dir']}")
    print("-"*80)

    # upcoming 6-hour blocks
    print(f"{'Time':<10} {'Icon':<25} {'Temp':<7} {'Precip':<8} {'Wind'}")
    print("-"*80)
    for period in weather['forecast_periods']:
        icon_name = period['icon'].split("/")[-1]  # remove path
        print(f"{period['time']:<10} {icon_name:<25} {period['temp']:<7} {period['precip']:<8} {period['wind']}")
    print("="*80)


if __name__ == "__main__":
    display_ascii()
