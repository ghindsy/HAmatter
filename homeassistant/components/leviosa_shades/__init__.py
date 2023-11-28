"""The Leviosa shades Zone integration."""
import logging

from leviosapy import LeviosaZoneHub as tZoneHub

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.COVER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Leviosa shades Zone from a config entry."""
    hub_name = entry.title
    hub_ip = entry.data["host"]
    hub = tZoneHub(
        hub_ip=hub_ip, hub_name=hub_name, websession=async_get_clientsession(hass)
    )
    await hub.getHubInfo()  # Check all is good
    _LOGGER.debug("Hub object created, FW: %s", hub.fwVer)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = hub

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
