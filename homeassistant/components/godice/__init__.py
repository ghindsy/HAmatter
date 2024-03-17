"""The godice integration."""

from __future__ import annotations

import logging

import bleak
import godice

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN

PLATFORMS = [Platform.SENSOR]
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up godice from a config entry."""
    _LOGGER.debug("Setup started")

    def on_disconnect_callback(_ble_data):
        _LOGGER.debug("on_disconnect_callback called")
        is_disconnected_by_request = hass.data[DOMAIN][entry.entry_id][
            "is_disconnected_by_request"
        ]
        if not is_disconnected_by_request:
            hass.create_task(hass.config_entries.async_reload(entry.entry_id))

    ble_device = bluetooth.async_ble_device_from_address(hass, entry.data["address"])
    assert ble_device is not None
    client = bleak.BleakClient(
        ble_device, timeout=20, disconnected_callback=on_disconnect_callback
    )
    dice = godice.create(client, godice.Shell.D6)
    try:
        await dice.connect()
        await dice.pulse_led(
            pulse_count=2, on_time_ms=50, off_time_ms=20, rgb_tuple=(0, 255, 0)
        )
    except Exception as err:
        raise ConfigEntryNotReady("Device not found") from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "device": dice,
        "device_info": create_devinfo(entry),
        "is_disconnected_by_request": False,
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading entry")
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    # prevent disconnect callback from integration reloading when disconnected by a user
    hass.data[DOMAIN][entry.entry_id]["is_disconnected_by_request"] = True
    device = hass.data[DOMAIN][entry.entry_id]["device"]
    await device.disconnect()
    hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


def create_devinfo(conf_entry: ConfigEntry):
    """Set device info displayed in HA."""
    dev_name = conf_entry.data["name"]
    return DeviceInfo(
        identifiers={(DOMAIN, dev_name)},
        name=dev_name,
        manufacturer="Particula",
        model="GoDice",
        sw_version="unknown",
    )
