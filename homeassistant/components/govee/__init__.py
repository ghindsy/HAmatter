"""The Govee LED strips integration."""
import asyncio
import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from govee_api_laggat import Govee
from homeassistant.exceptions import PlatformNotReady

from .const import DOMAIN, CONF_API_KEY

_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

# supported platforms
PLATFORMS = ["light"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Govee LED strips component."""
    hass.data[DOMAIN] = {}
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Govee LED strips from a config entry."""

    # get vars from ConfigFlow
    config = entry.data
    api_key = config[CONF_API_KEY]

    # Setup connection with devices/cloud
    hub = await Govee.create(api_key)
    # keep reference for disposing
    hass.data[DOMAIN] = {}
    hass.data[DOMAIN]["hub"] = hub

    # Verify that passed in configuration works
    devices, err = await hub.get_devices()
    if err:
        _LOGGER.warning("Could not connect to Govee API: " + err)
        await hub.rate_limit_delay()
        await async_unload_entry(hass, entry)
        raise PlatformNotReady()

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
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
        hub = hass.data[DOMAIN].pop("hub")
        await hub.close()

    return unload_ok
