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

In order to run the code locally ie. to test using `ascii.py` (assumes [asdf](https://asdf-vm.com/)):

```
asdf install
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

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

# Update configuration
ENABLE_AUTO_UPDATE = True # set to True to enable automatic updates from GitHub (default: False/disabled)
```

### 4. Upload to Inky Frame

1. Copy the `boot.py`, `weather_utils.py`, `update.py` and `main.py` files to the Inky Frame
2. `boot.py` runs first on boot, then `main.py` will run automatically
3. `update.py` will be used to update the files from GitHub (set `ENABLE_AUTO_UPDATE = False` in `secrets.py` if testing / modifying code on the device itself)

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

The device can update `main.py` and `weather_utils.py` from GitHub. Auto-updates are disabled by default and can be enabled by setting `ENABLE_AUTO_UPDATE = True` in `secrets.py` (useful when testing or modifying code directly on the device, keep it disabled).

To prevent bricking due to broken updates, it uses a **simplified rollback system**:

1. **Updating files**  
   - Each file is backed up as `file.prev` before replacement when updates are fetched from GitHub.
   - Updates happen at the start of each cycle (if `ENABLE_AUTO_UPDATE = True`).

2. **Boot sequence**  
   - `boot.py` runs first on every boot (before `main.py`)
   - It checks the consecutive failure count
   - If failures >= 3, it automatically rolls back all files to their `.prev` versions **before** `main.py` runs
   - This ensures rollback works even if `main.py` has syntax errors or can't import

3. **Failure tracking**  
   - After the main loop completes successfully, `mark_boot_success()` resets the failure count to 0.
   - If the main loop fails (exception) or `main.py` can't be imported, `mark_boot_failure()` increments the failure count.
   - The failure count tracks consecutive boot failures.

This means that:

- Rollback happens **before** `main.py` runs, so even completely broken `main.py` files can be recovered
- After 3 consecutive boot failures, the device automatically rolls back to the previous working version
- Successful boots reset the failure counter, so temporary issues don't trigger rollback
- The system is simple: just track consecutive failures, rollback when threshold is reached

The update should occur during each cycle (eg. every hour, when the device wakes from sleep / refreshes), though can be forced by restarting the device.

## License

This project uses data from the Yr.no API, which requires attribution. Make sure to comply with their [Terms of Service](https://developer.yr.no/doc/TermsOfService/).

Weather icons are from [Erik Flowers' Weather Icons collection](https://github.com/erikflowers/weather-icons).
