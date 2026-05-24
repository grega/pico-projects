# Inky Frame Weather Dashboard

A weather dashboard for the Pimoroni Inky Frame 7.3" E Ink display that fetches live weather data from the [Yr.no API](https://developer.yr.no/).

![DSCF3305](https://github.com/user-attachments/assets/48a00da3-b11b-46da-b9d3-e65492da8501)

***

This is similar to the "card" view that YR provides, eg. https://www.yr.no/en/content/2-2654991/card.html

(the values shown by the card can be used to verify the data shown on the Inky Frame)

See the YR docs on how to generate a card view URL for your location: https://developer.yr.no/doc/guides/available-widgets/

## Hardware Requirements

- [Pimoroni Inky Frame 7.3"](https://shop.pimoroni.com/products/inky-frame-7-3?variant=40541882056787) (Spectra 6 display)
- MicroSD card
- WiFi connection
- USB power (this version keeps the CPU awake to serve the status webserver; battery operation is not supported)

The snap-on case was sourced from [MakerWorld](https://makerworld.com/en/models/210940-inky-frame-7-3-clean-cover-snap-on-easy-print#profileId-230780) and printed using PLA.

## Setup Instructions

See Pimoroni's installation guide to get the firmware installed: https://github.com/pimoroni/inky-frame

In order to run the code locally ie. to test the display output using `ascii.py` (assumes [asdf](https://asdf-vm.com/)):

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

Configuration is split into two files:

- `secrets.py` - WiFi credentials only. Never pushed over the network.
- `config.py` - per-device settings (location, refresh interval). Round-tripped via `push.py`.

Create `secrets.py` on the Inky Frame's Pico:

```python
# secrets.py - WiFi credentials only
WIFI_SSID = "your-wifi-ssid"
WIFI_PASSWORD = "your-wifi-password"
```

And `config.py`:

```python
# config.py - Per-device runtime configuration
LOCATION_NAME = "Location name"
LATITUDE  = 00.0000  # max 4 decimal places
LONGITUDE = 00.0000  # max 4 decimal places
UTC_OFFSET_HOURS = 0  # eg. for BST use 1, for CEST use 2
SLEEP_INTERVAL_MINUTES = 60  # minutes between fetch + render cycles
```

### 4. Upload to Inky Frame

Bootstrap once over USB (with Thonny or `mpremote`): copy `main.py`, `webserver.py`, `dashboard.py`, `screen.py`, `ascii.py`, `weather_utils.py`, `config.py`, and `secrets.py` to the device.

`main.py` is the single entry point - it installs the log capture, mounts the SD card, connects to WiFi, starts the status webserver, then enters the fetch/render loop.

After the first boot, all subsequent code/config changes can be pushed over WiFi using [`push.py`](./push.py) (see below) - no need to re-plug USB.

## Pushing updates

[`push.py`](./push.py) is a small dev-side script that POSTs files to the device's webserver and triggers a reboot. The device's IP is printed on boot - write it to `.push_host` (one line) so `push.py` finds it automatically. (Or pass `--host <ip>`, or set the `INKY_HOST` env var.)

```bash
echo "192.168.1.42" > .push_host

./push.py code                                # push main.py and reboot
./push.py file dashboard.py                   # push any .py file and reboot
./push.py file webserver.py dashboard.py      # push multiple files, reboot once at the end
./push.py config fetch                        # download device config.py into _device/config.py
./push.py config push                         # upload _device/config.py and reboot
./push.py reboot                              # just reboot
```

`secrets.py` is intentionally not pushable - credentials are bootstrapped once over USB and never traverse the LAN.

## Status dashboard

While the device is running, point a browser at `http://<device-ip>/` for a live status page (auto-refreshes every 5s):

- **Device**: IP, local time, uptime, WiFi RSSI, free heap.
- **Weather fetch**: location, last fetch age + status, next refresh ETA.
- Footer links: `/status` (JSON snapshot), `/logs` (4 KB RAM ring buffer of all `print()` output), `/ascii` (ASCII render of the latest weather), `/config` (current `config.py` source).
- Reboot button (POSTs to `/reboot`).

Useful for `curl`:

```bash
curl http://<device-ip>/status | jq
curl http://<device-ip>/logs
```

> The webserver pauses briefly (~30 s) during each e-ink redraw - refreshes will hang until the render completes, then resume.

## ASCII Output

The code can also be run in a standard Python environment (ie. not on the Inky Frame) to see the weather data printed in ASCII format in the console, this is pretty handy for testing without having to plug in the device / wait for the display to refresh for each change.

`ascii.py` reads `LOCATION_NAME`, `LATITUDE`, `LONGITUDE`, and `UTC_OFFSET_HOURS` from `config.py` (the same file pushed to the device). No `secrets.py` is needed for the ASCII harness.

Then run:

```bash
python ascii.py
```

```text
================================================================================
Weather for Location-Name
Thu 4th Dec
--------------------------------------------------------------------------------
Temperature:         7°C
Icon:                wi-cloudy.jpg

Cloud:               100%
Pressure:            996 hPa
Humidity:            84%
Precipitation:       0.0 mm
Wind:                6 m/s
Direction:           WSW
--------------------------------------------------------------------------------
Time       Temp    Icon                      Precip   Wind
--------------------------------------------------------------------------------
13-18      8°C     wi-cloudy.jpg             0.0 mm   6 m/s
18-00      4°C     wi-night-clear.jpg        0.0 mm   4 m/s
00-06      2°C     wi-night-alt-cloudy.jpg   0.0 mm   3 m/s
06-12      2°C     wi-cloudy.jpg             0.1 mm   3 m/s
================================================================================
```

## License

This project uses data from the Yr.no API. Make sure to comply with their [Terms of Service](https://developer.yr.no/doc/TermsOfService/).

Weather icons are from [Erik Flowers' Weather Icons collection](https://github.com/erikflowers/weather-icons).
