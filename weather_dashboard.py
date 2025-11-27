import inky_frame
from picographics import PicoGraphics, DISPLAY_INKY_FRAME_7 as DISPLAY
import jpegdec
import urequests
import json

# Mount SD card
try:
    import os
    import machine
    import sdcard
    
    # Initialize SPI for SD card
    spi = machine.SPI(0, baudrate=40000000, sck=machine.Pin(18), mosi=machine.Pin(19), miso=machine.Pin(16))
    cs = machine.Pin(22)
    
    # Mount SD card
    sd = sdcard.SDCard(spi, cs)
    os.mount(sd, '/sd')
    print("SD card mounted successfully at /sd")
except Exception as e:
    print(f"Failed to mount SD card: {e}")

# Initialize display (800x480)
graphics = PicoGraphics(display=DISPLAY)

# Create JPEG decoder
jpeg = jpegdec.JPEG(graphics)

# Inky Frame 7.3" colors - CORRECTED MAPPINGS for Spectra 6
WHITE = inky_frame.WHITE
BLACK = inky_frame.BLACK
YELLOW = inky_frame.GREEN    # GREEN constant shows YELLOW
RED = inky_frame.BLUE        # BLUE constant shows RED
BLUE = inky_frame.YELLOW     # YELLOW constant shows BLUE
GREEN = inky_frame.ORANGE    # ORANGE constant shows GREEN

# Clear display to white
graphics.set_pen(WHITE)
graphics.clear()

# Location configuration
LAT = 51.3510
LON = -2.2632
LOCATION_NAME = "Bradford-on-Avon"

# Fetch weather data from Yr.no API
def fetch_weather():
    """Fetch weather data from Yr.no API"""
    url = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={LAT}&lon={LON}"
    headers = {"User-Agent": "InkyFrameWeather/1.0"}
    
    try:
        print(f"Fetching weather from {url}")
        response = urequests.get(url, headers=headers)
        data = response.json()
        response.close()
        return data
    except Exception as e:
        print(f"Error fetching weather: {e}")
        return None

# Map Yr.no symbol codes to icon filenames
def get_icon_filename(symbol_code):
    """Map Yr.no symbol code to local icon filename"""
    # Remove day/night/polartwilight suffix
    base_symbol = symbol_code.split('_')[0]
    
    # Map to Erik Flowers icon names
    icon_map = {
        "clearsky": "wi-day-sunny",
        "cloudy": "wi-cloudy",
        "fair": "wi-day-cloudy",
        "fog": "wi-fog",
        "heavyrain": "wi-rain",
        "heavyrainandthunder": "wi-thunderstorm",
        "heavyrainshowers": "wi-showers",
        "heavysleet": "wi-sleet",
        "heavysleetandthunder": "wi-sleet",
        "heavysleetshowers": "wi-sleet",
        "heavysnow": "wi-snow",
        "heavysnowandthunder": "wi-snow",
        "heavysnowshowers": "wi-snow",
        "lightrain": "wi-sprinkle",
        "lightrainandthunder": "wi-storm-showers",
        "lightrainshowers": "wi-showers",
        "lightsleet": "wi-sleet",
        "lightsleetandthunder": "wi-sleet",
        "lightsleetshowers": "wi-sleet",
        "lightsnow": "wi-snow",
        "lightsnowandthunder": "wi-snow",
        "lightsnowshowers": "wi-snow",
        "lightssleetshowersandthunder": "wi-sleet",
        "lightssnowshowersandthunder": "wi-snow",
        "partlycloudy": "wi-day-cloudy",
        "rain": "wi-rain",
        "rainandthunder": "wi-thunderstorm",
        "rainshowers": "wi-showers",
        "sleet": "wi-sleet",
        "sleetandthunder": "wi-sleet",
        "sleetshowers": "wi-sleet",
        "snow": "wi-snow",
        "snowandthunder": "wi-snow",
        "snowshowers": "wi-snow",
    }
    
    icon_name = icon_map.get(base_symbol, "wi-cloud")
    return f"/sd/weather-icons/{icon_name}.jpg"

# Parse weather data
def parse_weather(data):
    """Extract relevant weather information from API response"""
    if not data or 'properties' not in data:
        return None
    
    timeseries = data['properties']['timeseries']
    if not timeseries:
        return None
    
    # Current weather (first entry)
    current = timeseries[0]
    current_data = current['data']['instant']['details']
    
    # Get current symbol - try next_1_hours first, then next_6_hours
    current_symbol = 'cloudy'
    if 'next_1_hours' in current['data'] and 'summary' in current['data']['next_1_hours']:
        current_symbol = current['data']['next_1_hours']['summary']['symbol_code']
    elif 'next_6_hours' in current['data'] and 'summary' in current['data']['next_6_hours']:
        current_symbol = current['data']['next_6_hours']['summary']['symbol_code']
    
    # Define time blocks
    time_blocks = [
        "00-06",
        "06-12", 
        "12-18",
        "18-00"
    ]
    
    # Get current hour to determine which block to start from
    from time import localtime
    current_hour = localtime()[3]
    
    # Determine starting block
    if current_hour < 6:
        start_block = 0
    elif current_hour < 12:
        start_block = 1
    elif current_hour < 18:
        start_block = 2
    else:
        start_block = 3
    
    # Extract forecast periods (4 x 6-hour blocks)
    forecast_periods = []
    for block_idx in range(4):
        # Calculate which time block this is (wrapping around)
        actual_block = (start_block + block_idx) % 4
        time_label = time_blocks[actual_block]
        
        # Find the closest entry in the timeseries for this 6-hour block
        # Each block represents 6 hours ahead
        entry_idx = min(block_idx * 6, len(timeseries) - 1)
        entry = timeseries[entry_idx]
        
        details = entry['data']['instant']['details']
        
        # Get symbol - try next_6_hours first, then next_1_hours
        symbol = 'cloudy'
        if 'next_6_hours' in entry['data'] and 'summary' in entry['data']['next_6_hours']:
            symbol = entry['data']['next_6_hours']['summary']['symbol_code']
        elif 'next_1_hours' in entry['data'] and 'summary' in entry['data']['next_1_hours']:
            symbol = entry['data']['next_1_hours']['summary']['symbol_code']
        
        # Get precipitation amount
        precip = 0
        if 'next_6_hours' in entry['data'] and 'details' in entry['data']['next_6_hours']:
            precip = entry['data']['next_6_hours']['details'].get('precipitation_amount', 0)
        elif 'next_1_hours' in entry['data'] and 'details' in entry['data']['next_1_hours']:
            precip = entry['data']['next_1_hours']['details'].get('precipitation_amount', 0)
        
        forecast_periods.append({
            "time": time_label,
            "icon": get_icon_filename(symbol),
            "temp": str(round(details.get('air_temperature', 0))),
            "precip": f"{precip} mm",
            "wind": str(round(details.get('wind_speed', 0)))
        })
    
    return {
        "current_temp": str(round(current_data.get('air_temperature', 0))),
        "feels_like": str(round(current_data.get('air_temperature', 0))),  # Yr doesn't provide feels_like
        "current_precip": "0 mm",
        "current_wind": f"{round(current_data.get('wind_speed', 0))} m/s",
        "current_icon": get_icon_filename(current_symbol),
        "forecast_periods": forecast_periods
    }

# Function to draw JPEG icon
def draw_icon(filename, x, y, width, height):
    """Draw a JPEG icon at the specified position and size"""
    try:
        jpeg.open_file(filename)
        jpeg.decode(x, y, jpegdec.JPEG_SCALE_FULL)
    except Exception as e:
        # Draw a placeholder circle in red to indicate error
        graphics.set_pen(RED)
        graphics.circle(x + width//2, y + height//2, min(width, height)//2)

# Fetch and parse weather
print("Fetching weather data...")
weather_data = fetch_weather()
weather = parse_weather(weather_data)

if not weather:
    print("Failed to fetch weather, using dummy data")
    weather = {
        "current_temp": "10",
        "feels_like": "7",
        "current_precip": "0 mm",
        "current_wind": "5 m/s",
        "current_icon": "/sd/weather-icons/wi-cloud.jpg",
        "forecast_periods": [
            {"time": "00-06", "icon": "/sd/weather-icons/wi-cloud.jpg", "temp": "10", "precip": "0.2 mm", "wind": "5"},
            {"time": "06-12", "icon": "/sd/weather-icons/wi-cloud.jpg", "temp": "10", "precip": "0.4 mm", "wind": "5"},
            {"time": "12-18", "icon": "/sd/weather-icons/wi-cloud.jpg", "temp": "10", "precip": "0.1 mm", "wind": "6"},
            {"time": "18-00", "icon": "/sd/weather-icons/wi-day-cloudy.jpg", "temp": "13", "precip": "0.1 mm", "wind": "7"},
        ]
    }

# Header - location with blue accent
graphics.set_pen(BLUE)
graphics.rectangle(15, 15, 6, 50)
graphics.set_pen(BLACK)
graphics.set_font("bitmap8")
graphics.text(LOCATION_NAME, 30, 20, scale=3)

# Left section: Icon and main temp
draw_icon(weather['current_icon'], 30, 70, 100, 100)
graphics.set_pen(RED)
graphics.text(f"{weather['current_temp']}°", 150, 80, scale=8)

# Middle section: Feels like
graphics.set_pen(BLACK)
graphics.text("Feels like", 340, 90, scale=2)
graphics.set_pen(RED)
graphics.text(f"{weather['feels_like']}°", 340, 120, scale=5)

# Right section: Precipitation and Wind
graphics.set_pen(BLACK)
graphics.text("Precipitation", 520, 90, scale=2)
graphics.set_pen(BLUE)
graphics.text(weather['current_precip'], 520, 120, scale=3)

graphics.set_pen(BLACK)
graphics.text("Wind", 680, 90, scale=2)
graphics.text(weather['current_wind'], 680, 120, scale=3)

# Divider line in blue
graphics.set_pen(BLUE)
graphics.rectangle(20, 188, 760, 3)

# Forecast table
row_y = 210
row_height = 50
icon_size = 40

for i, period in enumerate(weather['forecast_periods']):
    # Draw row separator line
    if i > 0:
        graphics.set_pen(BLUE)
        graphics.line(20, row_y, 780, row_y)
    
    text_y = row_y + 15
    
    # Time
    graphics.set_pen(BLACK)
    graphics.text(period["time"], 30, text_y, scale=2)
    
    # Weather icon
    icon_x = 200
    icon_y = row_y + (row_height - icon_size) // 2
    draw_icon(period["icon"], icon_x, icon_y, icon_size, icon_size)
    
    # Temperature - all in red
    graphics.set_pen(RED)
    graphics.text(f"{period['temp']}°", 380, text_y, scale=2)
    
    # Precipitation
    precip_val = float(period["precip"].replace(" mm", ""))
    if precip_val > 0:
        graphics.set_pen(BLUE)
    else:
        graphics.set_pen(BLACK)
    graphics.text(period["precip"], 530, text_y, scale=2)
    
    # Wind
    graphics.set_pen(BLACK)
    graphics.text(period["wind"], 700, text_y, scale=2)
    
    row_y += row_height

# Update display
print("Updating display...")
graphics.update()
print("Done!")

# Put to sleep (optional - saves power)
# inky_frame.sleep_for(3600)  # Sleep for 1 hour
