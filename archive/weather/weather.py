import inky_helper as ih
from picographics import PicoGraphics, DISPLAY_INKY_FRAME_SPECTRA_7 as DISPLAY
from inky_frame import BLACK, WHITE, RED
import jpegdec
import urequests
import time
import gc

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
    "url": "https://www.yr.no/en/content/2-2654991/card.html",
    "viewport": {
        "width": 800,
        "height": 480
    },
    "screenshotOptions": {
      "type": "jpeg",
      "quality": 100
    }
}

def show_error(text):
    """Display an error message on the screen."""
    graphics.set_pen(RED)
    graphics.rectangle(0, 10, WIDTH, 35)
    graphics.set_pen(BLACK)
    graphics.text(text, 5, 16, WIDTH, 2)
    graphics.update()

def fetch_and_display_jpeg():
    try:
        # Clear the screen
        graphics.set_pen(WHITE)
        graphics.clear()
        graphics.set_pen(BLACK)
        graphics.text("Fetching JPEG...", 10, 100, WIDTH, 3)
        graphics.update()

        # Make the POST request to fetch the JPEG
        response = urequests.post(
            API_URL,
            headers=HEADERS,
            json=PAYLOAD
        )

        if response.status_code == 200:
            # Save the JPEG to the filesystem
            with open("weather.jpg", "wb") as f:
                f.write(response.content)
            print("JPEG saved as weather.jpg")

            # Clear the screen again
            graphics.set_pen(WHITE)
            graphics.clear()

            # Create a JPEG decoder instance
            jpeg = jpegdec.JPEG(graphics)

            # Open and decode the JPEG
            try:
                jpeg.open_file("weather.jpg")
                jpeg.decode(0, 0, jpegdec.JPEG_SCALE_FULL, dither=True)  # Position at (0, 0)
            except OSError as e:
                show_error(f"Error: {str(e)}")

            # Update the display
            graphics.update()
        else:
            print(f"API Error: {response.status_code}")
            show_error(f"API Error: {response.status_code}")

    except Exception as e:
        print(f"Exception: {str(e)}")
        show_error(f"Exception: {str(e)}")

    finally:
        if 'response' in locals():
            response.close()
        gc.collect()  # Free up memory

# Run the function
fetch_and_display_jpeg()

