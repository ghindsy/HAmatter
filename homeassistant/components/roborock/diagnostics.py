"""Support for the Airzone diagnostics."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics.util import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_UNIQUE_ID
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import RoborockDataUpdateCoordinator

TO_REDACT_CONFIG = ["token", "sn", "rruid", CONF_UNIQUE_ID, "username", "uid"]

TO_REDACT_COORD = ["duid", "localKey", "mac", "bssid"]


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinators: dict[str, RoborockDataUpdateCoordinator] = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    return {
        "config_entry": async_redact_data(config_entry.as_dict(), TO_REDACT_CONFIG),
        "coordinators": {
            f"**REDACTED-{i}**": {
                "roborock_device_info": async_redact_data(
                    coordinator.roborock_device_info.as_dict(), TO_REDACT_COORD
                ),
                "api": coordinator.api.diagnostic_data,
            }
            for i, coordinator in enumerate(coordinators.values())
        },
    }
