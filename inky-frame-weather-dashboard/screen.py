"""E-ink screen rendering for the weather dashboard.

Owns the PicoGraphics + JPEG decoder + Spectra 6 colour palette so the rest of
the codebase doesn't need to know about display primitives. The layout itself
is declared as data (`_METRICS`, `_FORECAST_COLUMNS`) and rendered by short
loops - move a column by editing one tuple.
"""

import time

import inky_frame
import jpegdec
from picographics import PicoGraphics, DISPLAY_INKY_FRAME_7 as DISPLAY


# Spectra 6 colour mappings - the display reports different ordinals than the
# constant names suggest, so we alias them once here and use these everywhere.
WHITE = inky_frame.WHITE
BLACK = inky_frame.BLACK
YELLOW = inky_frame.GREEN
RED = inky_frame.BLUE
BLUE = inky_frame.YELLOW
GREEN = inky_frame.ORANGE

_graphics = PicoGraphics(display=DISPLAY)
_jpeg = jpegdec.JPEG(_graphics)


# ---------------------------------------------------------------------------
# Layout (declarative)
# ---------------------------------------------------------------------------

# Current-conditions metric columns.
# Label drawn at (x, label_y) scale=2, value drawn 30 px below scale=3.
_METRICS = [
    # (x, label_y, label,         weather_key,         value_pen)
    (350,  80, "Cloud",           "current_cloud",     GREEN),
    (350, 150, "Pressure",        "current_pressure",  GREEN),
    (510,  80, "Humidity",        "current_humidity",  BLUE),
    (510, 150, "Precipitation",   "current_precip",    BLUE),
    (690,  80, "Wind",            "current_wind",      BLACK),
    (690, 150, "Direction",       "current_wind_dir",  BLACK),
]

# Forecast row text columns (icon column handled separately). All scale=3.
_FORECAST_COLUMNS = [
    # (x, period_key, pen)
    (30,  "time",   BLACK),
    (200, "temp",   RED),
    (510, "precip", BLUE),
    (690, "wind",   BLACK),
]
_FORECAST_ICON_X = 345
_FORECAST_ICON_SIZE = 40
_FORECAST_ROW_HEIGHT = 55
_FORECAST_FIRST_ROW_Y = 240


# ---------------------------------------------------------------------------
# Date helper
# ---------------------------------------------------------------------------

_DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_MONTH_NAMES = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul",
                "Aug", "Sep", "Oct", "Nov", "Dec"]


def _ordinal_suffix(day):
    if 10 <= day % 100 <= 20:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")


def _format_date(utc_offset_hours):
    lt = time.localtime(time.time() + utc_offset_hours * 3600)
    return f"{_DAY_NAMES[lt[6]]} {lt[2]}{_ordinal_suffix(lt[2])} {_MONTH_NAMES[lt[1]]}"


# ---------------------------------------------------------------------------
# Drawing primitives
# ---------------------------------------------------------------------------

def _text(s, x, y, pen, scale):
    _graphics.set_pen(pen)
    _graphics.text(s, x, y, scale=scale)


def _clear():
    _graphics.set_pen(WHITE)
    _graphics.clear()
    _graphics.set_font("bitmap8")


def _draw_icon(filename, x, y, width):
    """Draw a 200 x 200 source JPEG scaled down to fit `width`. Falls back to
    a coloured circle on failure so a missing file is visually obvious instead
    of bringing down the render."""
    try:
        _jpeg.open_file(filename)
        if width <= 35:
            scale = jpegdec.JPEG_SCALE_EIGHTH
        elif width <= 60:
            scale = jpegdec.JPEG_SCALE_QUARTER
        elif width <= 120:
            scale = jpegdec.JPEG_SCALE_HALF
        else:
            scale = jpegdec.JPEG_SCALE_FULL
        _jpeg.decode(x, y, scale)
    except Exception:
        _graphics.set_pen(RED)
        _graphics.circle(x + width // 2, y + width // 2, width // 2)


# ---------------------------------------------------------------------------
# Public renderers
# ---------------------------------------------------------------------------

def render_error(title, subtitle=None):
    """Fill the screen with a simple error message (used for boot-time failures)."""
    _clear()
    _text(title, 100, 200, BLACK, 3)
    if subtitle:
        _text(subtitle, 100, 240, BLACK, 2)
    _graphics.update()


def render_weather(weather, location_name, utc_offset_hours):
    """Draw the weather dashboard from a parsed weather dict."""
    _clear()

    # Header: blue accent bar + location + date
    _graphics.set_pen(BLUE)
    _graphics.rectangle(15, 15, 6, 50)
    _text(location_name, 30, 20, BLACK, 3)
    _text(_format_date(utc_offset_hours), 600, 20, BLACK, 3)

    # Current conditions: icon + big temperature on the left, metric grid on the right
    _draw_icon(weather["current_icon"], 20, 70, 100)
    _text(weather["current_temp"], 140, 100, RED, 9)
    for x, label_y, label, key, pen in _METRICS:
        _text(label, x, label_y, BLACK, 2)
        _text(weather[key], x, label_y + 30, pen, 3)

    # Divider
    _graphics.set_pen(BLUE)
    _graphics.rectangle(20, 218, 760, 3)

    # Forecast rows: time / temp / icon / precip / wind
    row_y = _FORECAST_FIRST_ROW_Y
    for i, period in enumerate(weather["forecast_periods"]):
        if i > 0:
            _graphics.set_pen(BLUE)
            _graphics.line(20, row_y, 780, row_y)
        text_y = row_y + 17
        for x, key, pen in _FORECAST_COLUMNS:
            _text(period[key], x, text_y, pen, 3)
        _draw_icon(period["icon"], _FORECAST_ICON_X, row_y + 2, _FORECAST_ICON_SIZE)
        row_y += _FORECAST_ROW_HEIGHT

    _graphics.update()
