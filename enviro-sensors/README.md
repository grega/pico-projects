# Enviro custom scripts

Standalone MicroPython scripts for [Pimoroni Enviro](https://github.com/pimoroni/enviro) boards. Replaces the stock `enviro` library with a unified entrypoint (`main.py`) that loads board-specific sensor code based on `config.model`. Keeps the same Pimoroni UF2 dependency for sensor drivers.

## Supported boards

| Board | Module | Sensors |
|---|---|---|
| **Indoor** | `board_indoor.py` | BME688 (temp, humidity, pressure, gas/AQI), BH1745 (light, colour temperature) |
| **Weather** | `board_weather.py` | BME280 (temp, humidity, pressure), LTR-559 (light), wind vane, anemometer, rain gauge |
| **Urban** | `board_urban.py` | BME280 (temp, humidity, pressure), PMS5003I (PM1, PM2.5, PM10), MEMS microphone (noise) |

Set `model` in `config.py` to `"indoor"`, `"weather"`, or `"urban"` — no other code changes needed.

## Enviro firmware

Tested with version `0.2.0` of the Pimoroni firmware (likely to work fine with later verions).

Follow the guide here: https://github.com/pimoroni/enviro/blob/main/documentation/upgrading-firmware.md

Utilising the releases such as `pimoroni-enviro-v1.22.2-micropython-enviro-v0.2.0.uf2`.

Once the device has been flashed, connect to it via USB and remove *all* default files and folders, replacing them with all of the `.py` files from this repository. Modify the `config.py` as needed, then run `main.py` (`main.py` will also automatically be executed on boot).

## How it works

Each script runs a loop:

1. **Clock sync** — fetches time from `pool.ntp.org` via NTP, writes to the PCF85063A RTC. Re-syncs every `resync_frequency` hours.
2. **Read sensors** — takes a single reading from all onboard sensors. USB temperature compensation is applied when running on USB power (adjusts humidity accordingly).
3. **Save locally** — appends a CSV row to `readings/<date>.csv`. Column headings stored once in `readings/columns.txt`.
4. **Cache for upload** — writes a JSON file to `uploads/` containing the reading, device nickname, model, UID, current power mode (`usb`/`batt`), and current free disk percentage.
5. **Upload** — when cached file count reaches `upload_frequency`, connects to WiFi and POSTs each JSON to `upload_url`. Failed uploads are retried next cycle.
6. **Sleep** — on battery: sets an RTC alarm and powers off (board re-powers on alarm). On USB: `time.sleep()` until the next reading.

## Power management

- **VSYS_EN latch** — the power rail is latched (`Pin(2, Pin.OUT, value=True)`) as the very first action on boot, before any imports or delays. On battery wake from an RTC alarm, a hold capacitor keeps the board alive only briefly — if the latch happens too late, the board powers off before the script can run.
- **Dynamic `vbus_present`** — the USB power pin is read via a cached `Pin` object at the start of every loop cycle, so the device switches between USB and battery behaviour dynamically — including correct sleep mode and temperature compensation.
- **I2C bus reset** — 16 SCL toggles run at startup to recover from stuck transactions after an unclean reset (e.g. USB disconnect mid-operation).

## Disk space management

When free space drops below 10%, the script attempts to upload cached files. If uploads also fail, it **thins** the cache by removing every other JSON file — halving the count while preserving coverage across the full time range. Repeated thinning degrades resolution gracefully rather than losing a contiguous block of history.

## Upload payload fields

Each cached/uploaded JSON payload includes:

- `nickname`, `model`, `uid`, `timestamp`
- `readings` (sensor values)
- `power_mode` (`usb` or `batt`)
- `free_space` (current filesystem free space percentage)

### Worker and Storage

Create a [Cloudflare Worker](https://workers.cloudflare.com/) using the content of `worker.js`, bind the Worker to an R2 bucket (setting the variable name `enviro_r2` to the name of the bucket). The `upload_url` value in `config.py` should be the Worker's public URL (optionally, add HTTP auth to the Worker, and add the credentials to `config.py`).

## Configuration

All settings live in `config.py`:

| Setting | Description |
|---|---|
| `model` | Board type: `"indoor"`, `"weather"`, or `"urban"` |
| `wifi_ssid` / `wifi_password` | WiFi credentials |
| `wifi_country` | ISO 3166-1 alpha-2 code for regulatory domain (e.g. `GB`, `US`) |
| `nickname` | Device name included in upload payloads |
| `reading_frequency` | Minutes between readings (aligned to clock grid) |
| `upload_url` | HTTP endpoint for JSON uploads |
| `upload_frequency` | Number of cached readings before triggering upload |
| `http_username` / `http_password` | Optional HTTP Basic Auth |
| `resync_frequency` | Hours between NTP re-syncs |
| `usb_power_temperature_offset` | °C subtracted from temp when on USB power |
| `silent_mode` | `True` to disable all LEDs (activity + warning) |

## Supporting files

| File | Purpose |
|---|---|
| `main.py` | Unified entrypoint — shared logic (power, WiFi, NTP, CSV, upload, sleep) |
| `helpers.py` | Stateless utilities (datetime, file ops, disk space) |
| `board_indoor.py` | Indoor sensor init + read |
| `board_weather.py` | Weather sensor init + read (incl. wind/rain) |
| `board_urban.py` | Urban sensor init + read (incl. PMS5003I, mic) |
| `config.py` | Device configuration (model, WiFi, upload, schedule) |
| `logging.py` | Minimal file + stdout logger with 4 KB rotation |
| `worker.js` | Cloudflare Worker that receives JSON payloads and stores them in R2 |
| `battery.md` | Battery life estimates |

## Requirements

- Pimoroni custom MicroPython UF2 (provides `breakout_bme68x`, `breakout_bme280`, `breakout_bh1745`, `breakout_ltr559`, `pimoroni_i2c`, `pcf85063a`)
- Pico W with Enviro Indoor, Weather, or Urban board
- Cloudflare Worker with an R2 binding
