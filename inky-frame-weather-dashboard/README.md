# Inky Frame Weather Dashboard

A weather dashboard for the Pimoroni Inky Frame 7.3" E Ink display that fetches live weather data from the [Yr.no API](https://developer.yr.no/).

![IMG_3832](https://github.com/user-attachments/assets/83189050-6991-4218-a3bb-3c8c90bb6cc9)

***

This is similar to the "card" view that YR provides, eg. https://www.yr.no/en/content/2-2654991/card.html

(the values shown by the card can be used to verify the data shown on the Inky Frame)

See the YR docs on how to generate a card view URL for your location: https://developer.yr.no/doc/guides/available-widgets/

## Hardware Requirements

- [Pimoroni Inky Frame 7.3"](https://shop.pimoroni.com/products/inky-frame-7-3?variant=40541882056787) (Spectra 6 display)
- MicroSD card
- WiFi connection

The case case was sourced from [MakerWorld](https://makerworld.com/en/models/210940-inky-frame-7-3-clean-cover-snap-on-easy-print#profileId-230780) and printed using PLA.

## Setup Instructions

See Pimoroni's installation guide to get the firmware installed: https://github.com/pimoroni/inky-frame

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

## ASCII Output

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

## Self-update and fallback

The device can update `main.py` and `weather_utils.py` from GitHub. To prevent bricking due to broken updates, it uses a **boot-counter + rollback** system:

1. **Updating files**  
   - Each file is backed up as `file.prev` before replacement.
   - After each successful file update, the boot counter is incremented to track stability.

2. **Boot sequence / rollback**  
   - If a file update fails, the boot counter is incremented (`mark_boot_failure()`).
   - If the counter exceeds `MAX_RETRIES` (default 3), the device rolls back each updated file to its `.prev` version and resets the counter.

3. **Marking a version stable**  
   - After successfully updating a file from GitHub, `mark_boot_success()` increments the counter.
   - Once the counter reaches `STABLE_VALUE` (default 10), the version is considered stable and further rollbacks are not triggered.

This means that:

- Successful updates are auto-confirmed
- Broken updates are automatically reverted after a few failed boot attempts

The update should occur during each cycle (eg. every hour, when the device wakes from sleep / refreshes), though can be forced by restarting the device.

## License

This project uses data from the Yr.no API, which requires attribution. Make sure to comply with their [Terms of Service](https://developer.yr.no/doc/TermsOfService/).

Weather icons are from [Erik Flowers' Weather Icons collection](https://github.com/erikflowers/weather-icons).
