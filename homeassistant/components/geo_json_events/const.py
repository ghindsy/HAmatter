"""Define constants for the GeoJSON events integration."""
from __future__ import annotations

from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "geo_json_events"

PLATFORMS: Final = [Platform.GEO_LOCATION]

ATTR_EXTERNAL_ID: Final = "external_id"
DEFAULT_RADIUS_IN_KM: Final = 20.0
DEFAULT_SCAN_INTERVAL: Final = 300
FEED: Final = "feed"
SOURCE: Final = "geo_json_events"

SIGNAL_DELETE_ENTITY: Final = "geo_json_events_delete_{}"
SIGNAL_UPDATE_ENTITY: Final = "geo_json_events_update_{}"
