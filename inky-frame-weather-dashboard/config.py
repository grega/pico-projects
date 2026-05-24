# config.py - Per-device runtime configuration
#
# Edit on the device, then round-trip via:
#     ./push.py config fetch   # downloads into _device/config.py
#     ./push.py config push    # uploads _device/config.py and reboots
#
# WiFi credentials live in secrets.py and are never pushed over the network

# Location configuration
LOCATION_NAME = "Bradford-on-Avon"
LATITUDE  = 51.3469  # max 4 decimal places
LONGITUDE = -2.2558  # max 4 decimal places

# Time configuration
UTC_OFFSET_HOURS = 0  # eg. for BST use 1, for CEST use 2

# Display refresh cadence (minutes between fetch + render cycles)
SLEEP_INTERVAL_MINUTES = 60
