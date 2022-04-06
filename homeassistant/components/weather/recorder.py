"""Integration platform for recorder."""
from __future__ import annotations

from homeassistant.core import HomeAssistant, callback

from . import ATTR_FORECAST


@callback
def exclude_attributes(hass: HomeAssistant) -> set[str]:
    """Exclude (often large) forecasts from being recorded in the database."""
    return {ATTR_FORECAST}
