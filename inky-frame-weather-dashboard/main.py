import gc
import json
import machine
import network
import ntptime
import os
import sdcard
import time

import ascii
import dashboard
import logger
import screen
import webserver
from config import LOCATION_NAME, LATITUDE, LONGITUDE, UTC_OFFSET_HOURS, SLEEP_INTERVAL_MINUTES
from weather_utils import connect_wifi, fetch_weather, weather_url, parse_weather

# Install log capture as the very first thing we do so every subsequent print()
# is recorded - both in the RAM ring and (once SD is attached) on disk.
logger.install()

# ---------------------------------------------------------------------------
# State exposed to /status
# ---------------------------------------------------------------------------

_boot_ticks_ms = time.ticks_ms()
_last_fetch_ticks_ms = None
_last_fetch_ok = None
_last_fetch_error = None
_last_render_ticks_ms = None
_last_weather = None  # most recent parsed weather dict, served by /ascii
_reboot_requested = False

REFRESH_INTERVAL_MS = SLEEP_INTERVAL_MINUTES * 60 * 1000
POLL_INTERVAL_MS = 100


# ---------------------------------------------------------------------------
# Status snapshot (shared by /status JSON and dashboard HTML)
# ---------------------------------------------------------------------------

def _local_time_string():
    try:
        lt = time.localtime(time.time() + UTC_OFFSET_HOURS * 3600)
        return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
            lt[0], lt[1], lt[2], lt[3], lt[4], lt[5]
        )
    except Exception:
        return None


def _collect_status():
    wlan = network.WLAN(network.STA_IF)
    try:
        connected = wlan.isconnected()
    except Exception:
        connected = False

    now = time.ticks_ms()
    uptime_s = time.ticks_diff(now, _boot_ticks_ms) // 1000

    last_fetch_age_s = None
    if _last_fetch_ticks_ms is not None:
        last_fetch_age_s = time.ticks_diff(now, _last_fetch_ticks_ms) // 1000

    next_refresh_in_s = None
    if _last_render_ticks_ms is not None:
        remaining_ms = REFRESH_INTERVAL_MS - time.ticks_diff(now, _last_render_ticks_ms)
        next_refresh_in_s = max(0, remaining_ms // 1000)

    rssi = None
    ip = None
    if connected:
        try:
            ip = wlan.ifconfig()[0]
        except Exception:
            pass
        try:
            rssi = wlan.status("rssi")
        except Exception:
            pass

    return {
        "uptime_s": uptime_s,
        "free_heap_bytes": gc.mem_free(),
        "alloc_heap_bytes": gc.mem_alloc(),
        "wifi_connected": connected,
        "ip": ip,
        "rssi_dbm": rssi,
        "local_time": _local_time_string(),
        "location_name": LOCATION_NAME,
        "weather_url": weather_url(LATITUDE, LONGITUDE),
        "refresh_interval_minutes": SLEEP_INTERVAL_MINUTES,
        "last_fetch_age_s": last_fetch_age_s,
        "last_fetch_ok": _last_fetch_ok,
        "last_fetch_error": _last_fetch_error,
        "next_refresh_in_s": next_refresh_in_s,
    }


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------

def _is_safe_upload_target(name):
    if not name or not name.endswith(".py"):
        return False
    stem = name[:-3]
    if not stem:
        return False
    for ch in stem:
        if not (("a" <= ch <= "z") or ("A" <= ch <= "Z") or ("0" <= ch <= "9") or ch == "_"):
            return False
    return True


def _handle_index(body, query):
    return (200, "text/html; charset=utf-8", dashboard.render_status_html(_collect_status()))


def _handle_status(body, query):
    return (200, "application/json", json.dumps(_collect_status()))


def _handle_logs(body, query):
    payload = logger.get_logs()
    if "download=1" in query:
        # Trigger "Save as..." in the browser instead of inline display.
        return (200, "text/plain; charset=utf-8", payload,
                {"Content-Disposition": "attachment; filename=device.log"})
    return (200, "text/plain; charset=utf-8", payload)


def _handle_ascii(body, query):
    return (200, "text/plain; charset=utf-8",
            ascii.render_ascii(_last_weather, LOCATION_NAME, UTC_OFFSET_HOURS))


def _handle_get_config(body, query):
    try:
        with open("config.py", "rb") as f:
            return (200, "text/x-python", f.read())
    except OSError as e:
        return (500, "text/plain", f"Cannot read config.py: {e}")


def _handle_upload(body, query):
    target = None
    for pair in query.split("&"):
        if pair.startswith("path="):
            target = pair[len("path="):]
            break
    if not _is_safe_upload_target(target):
        return (400, "text/plain",
                f"path must be a simple .py filename (eg. main.py, config.py, dashboard.py), got {target!r}")
    try:
        with open(target, "wb") as f:
            f.write(body)
    except OSError as e:
        return (500, "text/plain", f"Write failed: {e}")
    return (200, "text/plain", f"Wrote {len(body)} bytes to {target}")


def _handle_reboot(body, query):
    global _reboot_requested
    _reboot_requested = True
    return (200, "text/plain", "Rebooting")


def _register_routes():
    webserver.route("GET",  "/",       _handle_index)
    webserver.route("GET",  "/status", _handle_status)
    webserver.route("GET",  "/logs",   _handle_logs)
    webserver.route("GET",  "/ascii",  _handle_ascii)
    webserver.route("GET",  "/config", _handle_get_config)
    webserver.route("POST", "/upload", _handle_upload)
    webserver.route("POST", "/reboot", _handle_reboot)


def _poll_webserver():
    webserver.poll()
    if _reboot_requested:
        # Give the FIN packet time to reach the client. 200ms was too short on
        # slower WiFi networks - the chip would reset before the close had
        # propagated, and push.py would see an RST instead of a clean FIN.
        time.sleep_ms(500)
        machine.reset()


# ---------------------------------------------------------------------------
# Weather fetch + render
# ---------------------------------------------------------------------------

def _mount_sd():
    try:
        spi = machine.SPI(0, baudrate=40000000,
                          sck=machine.Pin(18), mosi=machine.Pin(19), miso=machine.Pin(16))
        cs = machine.Pin(22)
        sd = sdcard.SDCard(spi, cs)
        os.mount(sd, "/sd")
        print("SD card mounted successfully at /sd")
        # Attach the on-disk log file now that /sd is writeable. Any pre-mount
        # log lines captured in the RAM ring will be flushed to the file.
        logger.attach_sd("/sd/logs")
    except Exception as e:
        print(f"Failed to mount SD card: {e}")


def _render_weather():
    """Fetch + draw the weather screen. Updates _last_fetch_* globals."""
    global _last_fetch_ticks_ms, _last_fetch_ok, _last_fetch_error, _last_weather

    _last_fetch_ticks_ms = time.ticks_ms()

    raw = fetch_weather(LATITUDE, LONGITUDE)
    if raw is None:
        _last_fetch_ok = False
        _last_fetch_error = "API fetch failed (see /logs)"
        screen.render_error("Weather fetch failed",
                            "API unreachable - check /logs")
        return

    weather = parse_weather(raw, UTC_OFFSET_HOURS)
    if not weather:
        _last_fetch_ok = False
        _last_fetch_error = "API returned unexpected data (see /logs)"
        screen.render_error("Weather parse failed",
                            "Unexpected API response - check /logs")
        return

    _last_fetch_ok = True
    _last_fetch_error = None
    _last_weather = weather

    print("Updating display...")
    screen.render_weather(weather, LOCATION_NAME, UTC_OFFSET_HOURS)
    print("Done")


def _safe_render():
    """Wrap _render_weather() so a failure marks status but never escapes."""
    global _last_fetch_ok, _last_fetch_error
    try:
        _render_weather()
    except Exception as e:
        _last_fetch_ok = False
        _last_fetch_error = f"{type(e).__name__}: {e}"
        logger.log_exception(e, label="Render failed")


# ---------------------------------------------------------------------------
# Boot + main loop
# ---------------------------------------------------------------------------

def main():
    global _last_render_ticks_ms

    print("Booting Inky Frame Weather...")
    _mount_sd()

    # Connect to WiFi, retrying forever with exponential backoff. Without WiFi
    # we can't start the webserver (no IP to bind to), so /logs is unreachable
    # in this state - that's why logs are mirrored to SD: a card pulled and
    # read on a laptop is the user's escape hatch when the device is offline.
    # The error screen is drawn exactly once: e-ink refresh takes ~30s,
    # longer than the early retry intervals, so re-rendering would block
    # recovery from a transient hiccup.
    backoff_s = 10
    attempts = 0
    while True:
        if connect_wifi():
            if attempts > 0:
                print(f"WiFi recovered after {attempts + 1} attempts")
            break
        attempts += 1
        if attempts == 1:
            print("Initial WiFi connect failed - entering retry loop")
            screen.render_error("WiFi Connection Failed",
                                "Retrying - logs on SD: /sd/logs/")
        print(f"WiFi attempt {attempts} failed; next retry in {backoff_s}s")
        time.sleep(backoff_s)
        backoff_s = min(backoff_s * 2, 300)  # cap at 5 min between attempts

    # Start the webserver before NTP / weather fetch so push.py can always reach us even if a later step throws
    _register_routes()
    webserver.start()

    try:
        print("Syncing time via NTP...")
        ntptime.settime()
        print("Time updated successfully.")
        logger.mark_ntp_synced()
    except Exception as e:
        print(f"Failed to sync NTP time: {e}")

    while True:
        now = time.ticks_ms()
        if _last_render_ticks_ms is None or \
                time.ticks_diff(now, _last_render_ticks_ms) >= REFRESH_INTERVAL_MS:
            _safe_render()
            _last_render_ticks_ms = time.ticks_ms()
            gc.collect()

        _poll_webserver()
        time.sleep_ms(POLL_INTERVAL_MS)


main()
