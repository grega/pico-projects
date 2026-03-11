# Enviro — Configuration
# ============================================================

# Board model — "indoor", "weather", or "urban"
model = "indoor"

# WiFi
wifi_ssid = ""
wifi_password = ""
wifi_country = "GB"

# Device identity
nickname = f"enviro-{model}-1"

# Reading schedule
reading_frequency = 5     # minutes between readings (aligned to clock grid)

# Upload settings
upload_url = "https://example.com/upload"
upload_frequency = 3      # cached readings before triggering upload
http_username = None      # set for HTTP Basic Auth (or None)
http_password = None

# Clock
resync_frequency = 24     # hours between NTP re-syncs

# USB power compensation — the USB regulator heats the board, skewing
# the temperature sensor. This offset is subtracted from the raw reading.
usb_power_temperature_offset = 2.1

# Silent mode — disables all LEDs (activity + warning)
silent_mode = False
