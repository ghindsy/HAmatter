"""Diagnostics support for Guardian."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import DATA_PAIRED_SENSOR_MANAGER, PairedSensorManager
from .const import DATA_COORDINATOR, DATA_COORDINATOR_PAIRED_SENSOR, DOMAIN
from .util import GuardianDataUpdateCoordinator

CONF_BSSID = "bssid"
CONF_SSID = "ssid"

TO_REDACT = {
    CONF_BSSID,
    CONF_SSID,
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]

    coordinators: dict[str, GuardianDataUpdateCoordinator] = data[DATA_COORDINATOR]
    paired_sensor_coordinators: dict[str, GuardianDataUpdateCoordinator] = data[
        DATA_COORDINATOR_PAIRED_SENSOR
    ]
    paired_sensor_manager: PairedSensorManager = data[DATA_PAIRED_SENSOR_MANAGER]

    # Simulate the pairing of a paired sensor:
    await paired_sensor_manager.async_pair_sensor("AABBCCDDEEFF")

    return {
        "entry": {
            "title": entry.title,
            "data": dict(entry.data),
        },
        "data": {
            "valve_controller": {
                uid: async_redact_data(coordinator.data, TO_REDACT)
                for uid, coordinator in coordinators.items()
            },
            "paired_sensors": {
                uid: async_redact_data(coordinator.data, TO_REDACT)
                for uid, coordinator in paired_sensor_coordinators.items()
            },
        },
    }
