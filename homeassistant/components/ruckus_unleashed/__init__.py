"""The Ruckus Unleashed integration."""
import asyncio

from pyruckus import Ruckus

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC

from .const import (
    COORDINATOR,
    DOMAIN,
    PLATFORMS,
    RESPONSE_MAC_ADDRESS,
    UNDO_UPDATE_LISTENERS,
)
from .coordinator import RuckusUnleashedDataUpdateCoordinator


async def async_setup(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the Ruckus Unleashed component."""
    hass.data[DOMAIN] = {}
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Ruckus Unleashed from a config entry."""
    try:
        ruckus = await hass.async_add_executor_job(
            Ruckus,
            entry.data[CONF_HOST],
            entry.data[CONF_USERNAME],
            entry.data[CONF_PASSWORD],
        )
    except ConnectionError as error:
        raise ConfigEntryNotReady from error

    coordinator = RuckusUnleashedDataUpdateCoordinator(hass, ruckus=ruckus)

    await coordinator.async_refresh()
    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    system_info = await hass.async_add_executor_job(ruckus.system_info)

    registry = await device_registry.async_get_registry(hass)
    ap_info = await hass.async_add_executor_job(ruckus.ap_info)
    for device in ap_info["AP"]["ID"].values():
        registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            connections={
                (CONNECTION_NETWORK_MAC, device[RESPONSE_MAC_ADDRESS]),
            },
            identifiers={
                (CONNECTION_NETWORK_MAC, device[RESPONSE_MAC_ADDRESS]),
            },
            manufacturer="Ruckus",
            name=device["Device Name"],
            model=device["Model"],
            sw_version=system_info["System Overview"]["Version"],
        )

    hass.data[DOMAIN][entry.entry_id] = {
        COORDINATOR: coordinator,
        UNDO_UPDATE_LISTENERS: [],
    }

    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        for listener in hass.data[DOMAIN][entry.entry_id][UNDO_UPDATE_LISTENERS]:
            listener()

        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
