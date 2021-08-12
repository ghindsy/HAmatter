"""Constants for the tractive integration."""

from datetime import timedelta

DOMAIN = "tractive"

RECONNECT_INTERVAL = timedelta(seconds=10)

ATTR_DAILY_GOAL = "daily_goal"
ATTR_MINUTES_ACTIVE = "minutes_active"

TRACKER_HARDWARE_STATUS_UPDATED = "tracker_hardware_status_updated"
TRACKER_POSITION_UPDATED = "tracker_position_updated"
TRACKER_ACTIVITY_STATUS_UPDATED = "tractive_tracker_activity_updated"

SERVER_UNAVAILABLE = "tractive_server_unavailable"
