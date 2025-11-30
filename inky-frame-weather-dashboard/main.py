import inky_frame
import jpegdec
import json
import machine
import network
import ntptime
import os
import sdcard
import time
import urequests

from picographics import PicoGraphics, DISPLAY_INKY_FRAME_7 as DISPLAY
from time import sleep

# local imports
from secrets import LOCATION_NAME, LATITUDE, LONGITUDE, UTC_OFFSET_HOURS, SLEEP_INTERVAL_MINUTES
import update
from weather_utils import connect_wifi, fetch_weather, weather_url, parse_weather, get_icon_filename, wind_direction_to_compass

while True:
    update.update_all()

    # if this fails, we assume a boot failure and mark it as such for rollback (see update.py)
    try:
        try:
            spi = machine.SPI(0, baudrate=40000000, sck=machine.Pin(18), mosi=machine.Pin(19), miso=machine.Pin(16))
            cs = machine.Pin(22)
            
            sd = sdcard.SDCard(spi, cs)
            os.mount(sd, '/sd')
            print("SD card mounted successfully at /sd")
        except Exception as e:
            print(f"Failed to mount SD card: {e}")

        graphics = PicoGraphics(display=DISPLAY)
        jpeg = jpegdec.JPEG(graphics)

        # color mappings for Spectra 6 display
        WHITE = inky_frame.WHITE
        BLACK = inky_frame.BLACK
        YELLOW = inky_frame.GREEN
        RED = inky_frame.BLUE
        BLUE = inky_frame.YELLOW
        GREEN = inky_frame.ORANGE

        graphics.set_pen(WHITE)
        graphics.clear()

        if not connect_wifi():
            graphics.set_pen(BLACK)
            graphics.set_font("bitmap8")
            graphics.text("WiFi Connection Failed", 100, 200, scale=3)
            graphics.text("Check credentials in secrets.py", 100, 240, scale=2)
            graphics.update()
            print("Sleeping for 5 minutes before retry...")
            inky_frame.sleep_for(5)
        else:
            try:
                print("Syncing time via NTP...")
                ntptime.settime()
                print("Time updated successfully.")
            except Exception as e:
                print(f"Failed to sync NTP time: {e}")

        def draw_icon(filename, x, y, width, height):
            try:
                jpeg.open_file(filename)
                # icons are 200x200
                if width <= 35:
                    jpeg.decode(x, y, jpegdec.JPEG_SCALE_EIGHTH)
                elif width <= 60:
                    jpeg.decode(x, y, jpegdec.JPEG_SCALE_QUARTER)
                elif width <= 120:
                    jpeg.decode(x, y, jpegdec.JPEG_SCALE_HALF)
                else:
                    jpeg.decode(x, y, jpegdec.JPEG_SCALE_FULL)
            except Exception as e:
                graphics.set_pen(RED)
                graphics.circle(x + width//2, y + height//2, min(width, height)//2)

        print(f"Fetching weather from {weather_url(LATITUDE, LONGITUDE)}")
        weather_data = fetch_weather(LATITUDE, LONGITUDE)
        weather = parse_weather(weather_data, UTC_OFFSET_HOURS)

        if not weather:
            print("Failed to fetch weather data")
            graphics.set_pen(BLACK)
            graphics.set_font("bitmap8")
            graphics.text("Fetching weather data failed", 150, 200, scale=3)
            graphics.text("Check your internet connection", 150, 240, scale=2)
            graphics.update()
            print("Sleeping for 10 minutes before retry...")
            inky_frame.sleep_for(10)

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
        graphics.text(date_str, 580, 20, scale=3)

        draw_icon(weather['current_icon'], 20, 70, 100, 100)
        graphics.set_pen(RED)
        graphics.text(weather['current_temp'], 140, 100, scale=9)

        x_pos = 480
        graphics.set_pen(BLACK)
        graphics.text("Humidity", x_pos, 80, scale=2)
        graphics.text(weather['current_humidity'], x_pos, 110, scale=3)

        graphics.text("Precipitation", x_pos, 150, scale=2)
        graphics.set_pen(BLUE)
        graphics.text(weather['current_precip'], x_pos, 180, scale=3)

        graphics.set_pen(BLACK)
        graphics.text("Wind speed", 660, 80, scale=2)
        graphics.text(weather['current_wind'], 660, 110, scale=3)

        graphics.text("Direction", 660, 150, scale=2)
        graphics.text(weather['current_wind_dir'], 660, 180, scale=3)

        graphics.set_pen(BLUE)
        graphics.rectangle(20, 218, 760, 3)

        row_y = 240
        row_height = 55
        icon_size = 40

        for i, period in enumerate(weather['forecast_periods']):
            if i > 0:
                graphics.set_pen(BLUE)
                graphics.line(20, row_y, 780, row_y)
            
            text_y = row_y + 17
            
            graphics.set_pen(GREEN)
            graphics.text(period["time"], 30, text_y, scale=3)
            
            icon_x = 200
            icon_y = row_y + 8
            draw_icon(period["icon"], icon_x, icon_y, icon_size, icon_size)
            
            graphics.set_pen(RED)
            graphics.text(period['temp'], 360, text_y, scale=3)
            
            graphics.set_pen(BLUE)
            graphics.text(period["precip"], 520, text_y, scale=3)
            
            graphics.set_pen(BLACK)
            graphics.text(period["wind"], 680, text_y, scale=3)
            
            row_y += row_height

        print("Updating display...")
        graphics.update()
        print("Done")
        
        update.mark_boot_success()

        # on battery power sleep_for() will put the device to sleep and then re-run main.py on wake
        # on USB power sleep_for() will just sleep for the specified time, so `while True:` near
        # the top of this file is needed in order to refresh the data / display
        print(f"Going to sleep for {SLEEP_INTERVAL_MINUTES} minutes...")
        inky_frame.sleep_for(SLEEP_INTERVAL_MINUTES)
        
    except Exception as e:
        print("Boot failure:", e)
        update.mark_boot_failure()
        update.rollback_if_needed()
