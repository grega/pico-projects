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

### 1. Prepare Weather Icons

Download and convert the Erik Flowers weather icons to JPEG format:

```bash
git clone https://github.com/erikflowers/weather-icons.git

# convert SVG icons to 50x50 JPEG with white background
cd weather-icons/svg
for file in wi-*.svg; do
  convert "$file" -background white -flatten -resize 50x50 "${file%.svg}.jpg"
done
```

### 2. Prepare SD Card

1. Format your SD card as FAT32
2. Create a folder called `weather-icons`
3. Copy all the `.jpg` icon files into this folder
4. Insert the SD card into your Inky Frame

### 3. Configure

Create or edit `secrets.py` on your Inky Frame and add your WiFi and location details:

```python
# secrets.py - Configuration file

# WiFi Configuration
WIFI_SSID = "your-wifi-ssid"
WIFI_PASSWORD = "your-wifi-password"

# Location Configuration
LOCATION_NAME = "Location name"
LATITUDE  = 00.0000 # max 4 decimal places
LONGITUDE = 00.0000 # max 4 decimal places
```

### 4. Upload to Inky Frame

1. Save the file as `main.py` on the Inky Frame

## Display Layout

```
┌─────────────────────────────────────────────────────┐
│ Location Name                        Tue 24th May   │
│                                                      │
│ [Icon] 10°    Feels like 7°    Precipitation   Wind │
│                                0 mm             5 m/s│
├─────────────────────────────────────────────────────┤
│ Time  │ Icon │ Temp │ Precip │ Wind                 │
├─────────────────────────────────────────────────────┤
│ 00-06 │  ☁   │ 10°  │ 0.2 mm │  5                   │
│ 06-12 │  ☁   │ 10°  │ 0.4 mm │  5                   │
│ 12-18 │  ☁   │ 10°  │ 0.1 mm │  6                   │
│ 18-00 │  ⛅  │ 13°  │ 0.1 mm │  7                   │
└─────────────────────────────────────────────────────┘
```

## License

This project uses data from the Yr.no API, which requires attribution. Make sure to comply with their [Terms of Service](https://developer.yr.no/doc/TermsOfService/).
