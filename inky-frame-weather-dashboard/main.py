import builtins
import gc
import json
import machine
import network
import ntptime
import os
import sdcard
import time

import inky_frame
import jpegdec
from picographics import PicoGraphics, DISPLAY_INKY_FRAME_7 as DISPLAY

import ascii
import dashboard
import webserver
from config import LOCATION_NAME, LATITUDE, LONGITUDE, UTC_OFFSET_HOURS, SLEEP_INTERVAL_MINUTES
from secrets import WIFI_SSID, WIFI_PASSWORD
from weather_utils import connect_wifi, fetch_weather, weather_url, parse_weather

# ---------------------------------------------------------------------------
# In-memory log ring buffer + print() monkey-patch
# ---------------------------------------------------------------------------

_LOG_BUFFER_BYTES = 4096


class _LogBuffer:
    def __init__(self, size):
        self.buf = bytearray()
        self.size = size

    def write(self, data):
        self.buf.extend(data)
        overflow = len(self.buf) - self.size
        if overflow > 0:
            del self.buf[:overflow]


_log_buffer = _LogBuffer(_LOG_BUFFER_BYTES)


def _install_log_capture():
    original_print = builtins.print

    def _captured_print(*args, **kwargs):
        sep = kwargs.get("sep", " ")
        end = kwargs.get("end", "\n")
        try:
            _log_buffer.write((sep.join(str(a) for a in args) + end).encode())
        except Exception:
            pass
        return original_print(*args, **kwargs)

    builtins.print = _captured_print


_install_log_capture()

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
# Display setup
# ---------------------------------------------------------------------------

graphics = PicoGraphics(display=DISPLAY)
jpeg = jpegdec.JPEG(graphics)

# Spectra 6 colour mappings (display reports different ordinals than the names).
WHITE = inky_frame.WHITE
BLACK = inky_frame.BLACK
YELLOW = inky_frame.GREEN
RED = inky_frame.BLUE
BLUE = inky_frame.YELLOW
GREEN = inky_frame.ORANGE


def _draw_message(lines, body_colour=BLACK):
    graphics.set_pen(WHITE)
    graphics.clear()
    graphics.set_font("bitmap8")
    y = 200
    for i, (text, scale) in enumerate(lines):
        graphics.set_pen(body_colour if i == 0 else BLACK)
        graphics.text(text, 100, y, scale=scale)
        y += 40 * scale // 2 + 20
    graphics.update()


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
    return (200, "text/plain; charset=utf-8", bytes(_log_buffer.buf))


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
# Weather rendering (was app.py)
# ---------------------------------------------------------------------------


def _mount_sd():
    try:
        spi = machine.SPI(0, baudrate=40000000,
                          sck=machine.Pin(18), mosi=machine.Pin(19), miso=machine.Pin(16))
        cs = machine.Pin(22)
        sd = sdcard.SDCard(spi, cs)
        os.mount(sd, "/sd")
        print("SD card mounted successfully at /sd")
    except Exception as e:
        print(f"Failed to mount SD card: {e}")


def _draw_icon(filename, x, y, width, height):
    try:
        jpeg.open_file(filename)
        if width <= 35:
            jpeg.decode(x, y, jpegdec.JPEG_SCALE_EIGHTH)
        elif width <= 60:
            jpeg.decode(x, y, jpegdec.JPEG_SCALE_QUARTER)
        elif width <= 120:
            jpeg.decode(x, y, jpegdec.JPEG_SCALE_HALF)
        else:
            jpeg.decode(x, y, jpegdec.JPEG_SCALE_FULL)
    except Exception:
        graphics.set_pen(RED)
        graphics.circle(x + width // 2, y + height // 2, min(width, height) // 2)


def _render_weather():
    """Fetch + draw the weather screen. Updates _last_fetch_* globals."""
    global _last_fetch_ticks_ms, _last_fetch_ok, _last_fetch_error, _last_weather

    _last_fetch_ticks_ms = time.ticks_ms()

    print(f"Fetching weather from {weather_url(LATITUDE, LONGITUDE)}")
    weather_data = fetch_weather(LATITUDE, LONGITUDE)
    weather = parse_weather(weather_data, UTC_OFFSET_HOURS)

    if not weather:
        _last_fetch_ok = False
        _last_fetch_error = "weather fetch/parse failed"
        print("Failed to fetch weather data")
        graphics.set_pen(WHITE)
        graphics.clear()
        graphics.set_pen(BLACK)
        graphics.set_font("bitmap8")
        graphics.text("Fetching weather data failed", 150, 200, scale=3)
        graphics.text("Check your internet connection", 150, 240, scale=2)
        graphics.update()
        return

    _last_fetch_ok = True
    _last_fetch_error = None
    _last_weather = weather

    graphics.set_pen(WHITE)
    graphics.clear()

    graphics.set_pen(BLUE)
    graphics.rectangle(15, 15, 6, 50)
    graphics.set_pen(BLACK)
    graphics.set_font("bitmap8")
    graphics.text(LOCATION_NAME, 30, 20, scale=3)

    lt = time.localtime(time.time() + UTC_OFFSET_HOURS * 3600)
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    month_names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul",
                   "Aug", "Sep", "Oct", "Nov", "Dec"]
    day = lt[2]
    if 10 <= day % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    date_str = f"{day_names[lt[6]]} {day}{suffix} {month_names[lt[1]]}"
    graphics.set_pen(BLACK)
    graphics.text(date_str, 600, 20, scale=3)

    _draw_icon(weather["current_icon"], 20, 70, 100, 100)
    graphics.set_pen(RED)
    graphics.text(weather["current_temp"], 140, 100, scale=9)

    x_pos = 350
    graphics.set_pen(BLACK)
    graphics.text("Cloud", x_pos, 80, scale=2)
    graphics.set_pen(GREEN)
    graphics.text(weather["current_cloud"], x_pos, 110, scale=3)

    graphics.set_pen(BLACK)
    graphics.text("Pressure", x_pos, 150, scale=2)
    graphics.set_pen(GREEN)
    graphics.text(weather["current_pressure"], x_pos, 180, scale=3)

    x_pos = 510
    graphics.set_pen(BLACK)
    graphics.text("Humidity", x_pos, 80, scale=2)
    graphics.set_pen(BLUE)
    graphics.text(weather["current_humidity"], x_pos, 110, scale=3)

    graphics.set_pen(BLACK)
    graphics.text("Precipitation", x_pos, 150, scale=2)
    graphics.set_pen(BLUE)
    graphics.text(weather["current_precip"], x_pos, 180, scale=3)

    x_pos = 690
    graphics.set_pen(BLACK)
    graphics.text("Wind", x_pos, 80, scale=2)
    graphics.set_pen(BLACK)
    graphics.text(weather["current_wind"], x_pos, 110, scale=3)

    graphics.set_pen(BLACK)
    graphics.text("Direction", x_pos, 150, scale=2)
    graphics.set_pen(BLACK)
    graphics.text(weather["current_wind_dir"], x_pos, 180, scale=3)

    graphics.set_pen(BLUE)
    graphics.rectangle(20, 218, 760, 3)

    row_y = 240
    row_height = 55
    icon_size = 40

    for i, period in enumerate(weather["forecast_periods"]):
        if i > 0:
            graphics.set_pen(BLUE)
            graphics.line(20, row_y, 780, row_y)

        text_y = row_y + 17

        graphics.set_pen(BLACK)
        graphics.text(period["time"], 30, text_y, scale=3)

        graphics.set_pen(RED)
        graphics.text(period["temp"], 200, text_y, scale=3)

        _draw_icon(period["icon"], 345, row_y + 2, icon_size, icon_size)

        graphics.set_pen(BLUE)
        graphics.text(period["precip"], 510, text_y, scale=3)

        graphics.set_pen(BLACK)
        graphics.text(period["wind"], 690, text_y, scale=3)

        row_y += row_height

    print("Updating display...")
    graphics.update()
    print("Done")


def _safe_render():
    """Wrap _render_weather() so a failure marks status but never escapes."""
    global _last_fetch_ok, _last_fetch_error
    try:
        _render_weather()
    except Exception as e:
        _last_fetch_ok = False
        _last_fetch_error = f"{type(e).__name__}: {e}"
        print(f"Render failed: {_last_fetch_error}")


# ---------------------------------------------------------------------------
# Boot + main loop
# ---------------------------------------------------------------------------


def main():
    global _last_render_ticks_ms

    print("Booting Inky Frame Weather...")
    _mount_sd()

    if not connect_wifi():
        graphics.set_pen(WHITE)
        graphics.clear()
        graphics.set_pen(BLACK)
        graphics.set_font("bitmap8")
        graphics.text("WiFi Connection Failed", 100, 200, scale=3)
        graphics.text("Check credentials in secrets.py", 100, 240, scale=2)
        graphics.update()
        # Sit here polling nothing useful; with no WiFi the webserver can't
        # start either. machine.reset() would just loop, so wait and retry.
        time.sleep(300)
        machine.reset()

    # Start the webserver before NTP / weather fetch so push.py can always
    # reach us even if a later step throws.
    _register_routes()
    webserver.start()

    try:
        print("Syncing time via NTP...")
        ntptime.settime()
        print("Time updated successfully.")
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
