# Inky Frame Weather Dashboard

A weather dashboard for the Pimoroni Inky Frame 7.3" E Ink display that fetches live weather data from the [Yr.no API](https://developer.yr.no/).

![IMG_3832](https://github.com/user-attachments/assets/83189050-6991-4218-a3bb-3c8c90bb6cc9)

Case from [MakerWorld](https://makerworld.com/en/models/210940-inky-frame-7-3-clean-cover-snap-on-easy-print#profileId-230780).

## Hardware Requirements

- [Pimoroni Inky Frame 7.3"](https://shop.pimoroni.com/products/inky-frame-7-3?variant=40541882056787) (Spectra 6 display)
- MicroSD card
- WiFi connection

## Setup Instructions

See Pimoroni's installation guide to get the firmware installed: https://github.com/pimoroni/inky-frame

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

# Time configuration
UTC_OFFSET_HOURS = 0 # eg. for BST use 1, for CEST use 2
SLEEP_INTERVAL_MINUTES = 60 # time in minutes between data / display updates
```

### 4. Upload to Inky Frame

1. Save the file as `main.py` on the Inky Frame

## Display Layout

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

## License

This project uses data from the Yr.no API, which requires attribution. Make sure to comply with their [Terms of Service](https://developer.yr.no/doc/TermsOfService/).

Weather icons are from [Erik Flowers' Weather Icons collection](https://github.com/erikflowers/weather-icons).
