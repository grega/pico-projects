import inky_helper as ih
from picographics import PicoGraphics, DISPLAY_INKY_FRAME_SPECTRA_7 as DISPLAY
from inky_frame import BLACK, WHITE
import pngdec
import urequests
import time

try:
    from secrets import WIFI_PASSWORD, WIFI_SSID
    ih.network_connect(WIFI_SSID, WIFI_PASSWORD)
except ImportError:
    print("Create secrets.py with your WiFi credentials")

# Initialize the display
graphics = PicoGraphics(DISPLAY)
WIDTH, HEIGHT = graphics.get_bounds()

# Cloudflare API details
API_URL = "https://api.cloudflare.com/client/v4/accounts/c37b1434e9c3d7c46cf23c17acd54595/browser-rendering/screenshot"
AUTH_TOKEN = "Bearer ***REMOVED***"
HEADERS = {
    "Authorization": AUTH_TOKEN,
    "Content-Type": "application/json"
}
PAYLOAD = {
    # "url": "https://www.yr.no/en/content/2-2654991/card.html",
    "url": "https://falling-silence-9db9.greg-annandale.workers.dev",
    "viewport": {
        "width": 800,
        "height": 480
    }
}

def fetch_and_display_png():
    try:
        # Clear the screen
        graphics.clear()

        # Make the POST request to fetch the PNG
        response = urequests.post(
            API_URL,
            headers=HEADERS,
            json=PAYLOAD
        )

        if response.status_code == 200:
            # Save the PNG to the filesystem
            with open("weather.png", "wb") as f:
                f.write(response.content)
            print("PNG saved as weather.png")

            # Clear the screen again
            graphics.set_pen(WHITE)
            graphics.clear()

            # Create a PNG decoder instance
            png = pngdec.PNG(graphics)

            # Open and decode the PNG
            try:
                png.open_file("weather.png")
                png.decode(0, 0)  # Position at (0, 0)
            except OSError as e:
                graphics.set_pen(BLACK)
                graphics.text(f"Error: {str(e)}", 10, 100, WIDTH, 3)

            # Update the display
            graphics.update()
        else:
            print(f"API Error: {response.status_code}")
            graphics.set_pen(BLACK)
            graphics.text(f"API Error: {response.status_code}", 10, 100, WIDTH, 3)
            graphics.update()

    except Exception as e:
        print(f"Exception: {str(e)}")
        graphics.set_pen(BLACK)
        graphics.text(f"Exception: {str(e)}", 10, 100, WIDTH, 3)
        graphics.update()

    finally:
        if 'response' in locals():
            response.close()

# Run the function
fetch_and_display_png()
