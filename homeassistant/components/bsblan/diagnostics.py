"""Diagnostics support for BSBLan."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .models import BSBLanData


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data: BSBLanData = hass.data[DOMAIN][entry.entry_id]

    return {
        "entry": {
            "title": entry.title,
            "data": dict(entry.data),
        },
        "info": data.info.to_dict(),
        "device": data.device.to_dict(),
        "coordinator_data": {
            "state": data.coordinator.data.state.to_dict()
            if data.coordinator.data
            else {},
        },
        "static": data.static.to_dict(),
    }
