"""Constants for the Switcher integration."""

DOMAIN = "switcher_kis"
DATA_DISCOVERY = "discovery"
DISCOVERY_TIME_SEC = 12

SIGNAL_DEVICE_ADD = "switcher_device_add"
CONF_USERNAME = "username"
CONF_TOKEN = "token"

COVER1_ID = "runner"
COVER2_ID = "runner2"

# Services
CONF_AUTO_OFF = "auto_off"
CONF_TIMER_MINUTES = "timer_minutes"
SERVICE_SET_AUTO_OFF_NAME = "set_auto_off"
SERVICE_TURN_ON_WITH_TIMER_NAME = "turn_on_with_timer"

# Defines the maximum interval device must send an update before it marked unavailable
MAX_UPDATE_INTERVAL_SEC = 30
