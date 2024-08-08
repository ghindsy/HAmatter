"""The bayesian component."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import discovery
from homeassistant.helpers.typing import ConfigType

from .binary_sensor import PLATFORM_SCHEMA  # noqa: F401
from .const import DOMAIN as BAYESIAN_DOMAIN

DOMAIN = BAYESIAN_DOMAIN
PLATFORMS = [Platform.BINARY_SENSOR]

_LOGGER = logging.getLogger(__name__)  # TODO delete-me


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Bayesian integration from YAML."""
    if DOMAIN not in config:
        return True

    for platform in PLATFORMS:
        hass.async_create_task(
            discovery.async_load_platform(hass, platform, DOMAIN, {}, config)
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Bayesian from a config entry."""
    _LOGGER.warning("Calling async_setup_entry() Entry : %s", entry)  # TODO delete me
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Scrape config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    _LOGGER.debug(
        "Options flow update for entry_id %s with options %s",
        entry.entry_id,
        entry.options,
    )
    hass.config_entries.async_schedule_reload(entry.entry_id)
