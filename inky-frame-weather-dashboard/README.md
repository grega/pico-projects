# Inky Frame Weather Dashboard

A weather dashboard for the Pimoroni Inky Frame 7.3" E Ink display that fetches live weather data from the Yr.no API.

This is similar to the "card" view that YR provides, eg. https://www.yr.no/en/content/2-2654991/card.html

(the values shown by the card can be used to verify the data shown on the Inky Frame)

See the YR docs for information on getting the location ID (`2-2654991`): https://developer.yr.no/doc/guides/available-widgets/

## Features

- Live weather data from Yr.no (MET Norway) API
- Current temperature, "feels like" temperature, precipitation, and wind speed
- 24-hour forecast in 6-hour blocks
- Weather icons from [Erik Flowers' weather-icons collection](https://github.com/erikflowers/weather-icons)
- Auto-refresh every hour
- Low power consumption with deep sleep mode

## Hardware Requirements

- Pimoroni Inky Frame 7.3" (Spectra 6 display)
- MicroSD card
- WiFi connection

## Setup Instructions

### 1. Copy weather icons to SD card

1. Format the SD card as FAT32
2. Copy the `./weather-icons` directory onto the SD card
3. Insert the SD card into the Inky Frame

### 3. Configure

Create or edit `secrets.py` on the Inky Frame and add your WiFi and location details:

```python
# secrets.py - Configuration file

# WiFi configuration
WIFI_SSID = "your-wifi-ssid"
WIFI_PASSWORD = "your-wifi-password"

# Location configuration
LOCATION_NAME = "Location name"
LATITUDE  = 00.0000 # max 4 decimal places
LONGITUDE = 00.0000 # max 4 decimal places

# Time configuration
UTC_OFFSET_HOURS = 0 # eg. for BST use 1, for CEST use 2
SLEEP_INTERVAL_MINUTES = 60 # time in minutes between data / display updates
```

### 4. Upload to Inky Frame

1. Copy the `weather_utils.py` and `main.py` files to the Inky Frame
2. `main.py` will run automatically on boot

## Display Layout

Roughly:

```
┌──────────────────────────────────────────────────────────────────┐
│ Location Name                              Tue 24th May          │
│                                                                  │
│ [Icon]    13°C   Humidity  Precipitation  Wind   Direction       │
│           93%      0 mm        7 m/s      WSW                    │
├──────────────────────────────────────────────────────────────────┤
│ Time   │ Icon          │ Temp │ Precip │ Wind                    │
├──────────────────────────────────────────────────────────────────┤
│ 00-06 │ [icon]        │ 10°C │ 0.2 mm │ 5 m/s                    │
│ 06-12 │ [icon]        │ 10°C │ 0.4 mm │ 5 m/s                    │
│ 12-18 │ [icon]        │ 10°C │ 0.1 mm │ 6 m/s                    │
│ 18-00 │ [icon]        │ 13°C │ 0.1 mm │ 7 m/s                    │
└──────────────────────────────────────────────────────────────────┘
```

## ASCI Output

The code can also be run in a standard Python environment (ie. not on the Inky Frame) to see the weather data printed in ASCII format in the console. 

Create a `secrets.py` file configured with location details:

```python
# secrets.py - Configuration file

# Location configuration
LOCATION_NAME = "Location name"
LATITUDE  = xx.xxxx # max 4 decimal places
LONGITUDE = -xx.xxxx # max 4 decimal places

# Time configuration
UTC_OFFSET_HOURS = 0 # eg. for BST use 1, for CEST use 2
```

Then run:

```bash
python ascii.py
```

This will output a table to the console with the current weather and forecast data, handy for testing / debugging without the hardware connected (or without waiting for the display to refresh):

```text
================================================================================
Weather for Bradford-on-Avon
Fri 28th Nov
--------------------------------------------------------------------------------
Current Temperature: 9°C
Current Humidity:    83%
Current Precip:      0.0 mm
Current Wind:        6 m/s (SSW)
Current Icon:        wi-cloudy.jpg
--------------------------------------------------------------------------------
Time       Icon                      Temp    Precip   Wind
--------------------------------------------------------------------------------
23-00      wi-rain.jpg               10°C    2.8 mm   8 m/s
00-06      wi-rain.jpg               10°C    4.7 mm   8 m/s
06-12      wi-rain.jpg               10°C    1.6 mm   7 m/s
12-18      wi-day-cloudy.jpg         8°C     0.0 mm   5 m/s
================================================================================
```

## License

This project uses data from the Yr.no API, which requires attribution. Make sure to comply with their [Terms of Service](https://developer.yr.no/doc/TermsOfService/).

Weather icons are from [Erik Flowers' Weather Iconscollection](https://github.com/erikflowers/weather-icons).
