"""Constants for Microbot."""
# Base component constants
NAME = "MicroBot Push"
DOMAIN = "keymitt_ble"
DOMAIN_DATA = f"{DOMAIN}_data"
VERSION = "2022.08.0"
MANUFACTURER = "Naran/Keymitt"

# Icons
ICON = "mdi:toggle-switch-variant"

# Device classes
BINARY_SENSOR_DEVICE_CLASS = "connectivity"

# Platforms
BINARY_SENSOR = "binary_sensor"
SENSOR = "sensor"
SWITCH = "switch"


# Configuration and options
CONF_ENABLED = "enabled"
CONF_NAME = "name"
CONF_PASSWORD = "password"
CONF_BDADDR = "bdaddr"
DEFAULT_RETRY_COUNT = 5

# Defaults
DEFAULT_NAME = "Microbot"
