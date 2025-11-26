import inky_frame
from picographics import PicoGraphics, DISPLAY_INKY_FRAME_7 as DISPLAY
import jpegdec

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
    print("Icons will be loaded from root filesystem instead")

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

# Fake weather data with icon filenames
# Convert icons to JPEG format (more reliable than PNG on MicroPython)
# Save JPEGs to SD card: /sd/weather-icons/wi-cloud.jpg, /sd/weather-icons/wi-day-rain.jpg, etc.
location = "Bradford-on-Avon"
current_temp = "10"
feels_like = "7"
current_precip = "0 mm"
current_wind = "5 m/s"
current_icon = "/sd/weather-icons/wi-cloud.jpg"

forecast_periods = [
    {"time": "23-00", "icon": "/sd/weather-icons/wi-cloud.jpg", "temp": "10", "precip": "0.2 mm", "wind": "5"},
    {"time": "00-06", "icon": "/sd/weather-icons/wi-cloud.jpg", "temp": "10", "precip": "0.4 mm", "wind": "5"},
    {"time": "06-12", "icon": "/sd/weather-icons/wi-cloud.jpg", "temp": "10", "precip": "0.1 mm", "wind": "6"},
    {"time": "12-18", "icon": "/sd/weather-icons/wi-day-cloudy.jpg", "temp": "13", "precip": "0.1 mm", "wind": "7"},
]

# Function to draw JPEG icon
def draw_icon(filename, x, y, width, height):
    """Draw a JPEG icon at the specified position and size"""
    try:
        # Attempt to open and decode the JPEG
        jpeg.open_file(filename)
        jpeg.decode(x, y, jpegdec.JPEG_SCALE_FULL)
        
    except Exception as e:
        # Draw a placeholder circle in red to indicate error
        graphics.set_pen(RED)
        graphics.circle(x + width//2, y + height//2, min(width, height)//2)

# Header - location with blue accent
graphics.set_pen(BLUE)
graphics.rectangle(15, 15, 6, 50)
graphics.set_pen(BLACK)
graphics.set_font("bitmap8")
graphics.text(location, 30, 20, scale=3)

# Left section: Icon and main temp
draw_icon(current_icon, 30, 70, 100, 100)
graphics.set_pen(RED)
graphics.text(f"{current_temp}°", 150, 80, scale=8)

# Middle section: Feels like
graphics.set_pen(BLACK)
graphics.text("Feels like", 340, 90, scale=2)
graphics.set_pen(RED)
graphics.text(f"{feels_like}°", 340, 120, scale=5)

# Right section: Precipitation and Wind
graphics.set_pen(BLACK)
graphics.text("Precipitation", 520, 90, scale=2)
graphics.set_pen(BLUE)
graphics.text(current_precip, 520, 120, scale=3)

graphics.set_pen(BLACK)
graphics.text("Wind", 680, 90, scale=2)
graphics.text(current_wind, 680, 120, scale=3)

# Divider line in blue
graphics.set_pen(BLUE)
graphics.rectangle(20, 188, 760, 3)

# Forecast table
row_y = 210
row_height = 50
icon_size = 40

for i, period in enumerate(forecast_periods):
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
graphics.update()

# Put to sleep (optional - saves power)
# inky_frame.sleep_for(3600)  # Sleep for 1 hour
