# Inky Frame Weather Dashboard

A weather dashboard for the Pimoroni Inky Frame 7.3" E Ink display that fetches live weather data from the Yr.no API.

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

1. Format your SD card as FAT32
2. Copy the `./weather-icons` directory onto the SD card
3. Insert the SD card into your Inky Frame

### 3. Configure

Create or edit `secrets.py` on your Inky Frame and add your WiFi and location details:

```python
# secrets.py - Configuration file

# WiFi configuration
WIFI_SSID = "your-wifi-ssid"
WIFI_PASSWORD = "your-wifi-password"

# Location configuration
LOCATION_NAME = "Location name"
LATITUDE  = 00.0000 # max 4 decimal places
LONGITUDE = 00.0000 # max 4 decimal places

# Timezone configuration
UTC_OFFSET_HOURS = 0 # eg. for BST use 1, for CEST use 2
```

### 4. Upload to Inky Frame

1. Save the file as `main.py` on the Inky Frame

## Display Layout

```
┌──────────────────────────────────────────────────────────────────┐
│ Location Name                              Tue 24th May          │
│                                                                   │
│ [Icon] 13°C   Humidity    Precipitation    Wind       Direction  │
│                  93%          0 mm         7 m/s         WSW     │
├──────────────────────────────────────────────────────────────────┤
│ Time  │ Icon │ Temp  │ Precip │ Wind                             │
├──────────────────────────────────────────────────────────────────┤
│ 00-06 │  🌙  │ 10°C  │ 0.2 mm │ 5 m/s                            │
│ 06-12 │  ☁   │ 10°C  │ 0.4 mm │ 5 m/s                            │
│ 12-18 │  ⛅  │ 10°C  │ 0.1 mm │ 6 m/s                            │
│ 18-00 │  🌙☁ │ 13°C  │ 0.1 mm │ 7 m/s                            │
└──────────────────────────────────────────────────────────────────┘
```

## License

This project uses data from the Yr.no API, which requires attribution. Make sure to comply with their [Terms of Service](https://developer.yr.no/doc/TermsOfService/).

Weather icons are from [Erik Flowers' Weather Iconscollection](https://github.com/erikflowers/weather-icons).
