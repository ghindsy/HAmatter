"""The Wyoming integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import ATTR_SPEAKER, DOMAIN
from .data import WyomingService
from .devices import SatelliteDevices
from .models import DomainDataItem
from .satellite import WyomingSatellite

_LOGGER = logging.getLogger(__name__)

SATELLITE_PLATFORMS = [Platform.BINARY_SENSOR, Platform.SELECT, Platform.SWITCH]

__all__ = [
    "ATTR_SPEAKER",
    "DOMAIN",
    "async_setup_entry",
    "async_unload_entry",
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Load Wyoming."""
    service = await WyomingService.create(entry.data["host"], entry.data["port"])

    if service is None:
        raise ConfigEntryNotReady("Unable to connect")

    satellite_devices = SatelliteDevices(hass, entry)
    satellite_devices.async_setup()

    item = DomainDataItem(service=service, satellite_devices=satellite_devices)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = item

    await hass.config_entries.async_forward_entry_setups(entry, service.platforms)
    entry.async_on_unload(entry.add_update_listener(update_listener))

    if (satellite_info := service.info.satellite) is not None:
        # Set up satellite sensors, switches, etc.
        await hass.config_entries.async_forward_entry_setups(entry, SATELLITE_PLATFORMS)

        # Run satellite connection in a separate task
        satellite_device = satellite_devices.async_get_or_create(
            name=satellite_info.name,
            suggested_area=satellite_info.area,
        )
        item.satellite = WyomingSatellite(hass, service, satellite_device)
        entry.async_create_background_task(
            hass,
            item.satellite.run(),
            f"Satellite {satellite_info.name}",
        )

        entry.async_on_unload(item.satellite.stop)

    return True


async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Wyoming."""
    item: DomainDataItem = hass.data[DOMAIN][entry.entry_id]

    unload_ok = await hass.config_entries.async_unload_platforms(
        entry,
        item.service.platforms,
    )
    if unload_ok:
        del hass.data[DOMAIN][entry.entry_id]

    return unload_ok
