"""The NEW_NAME integration."""
from __future__ import annotations

from spencerassistant.config_entries import ConfigEntry
from spencerassistant.const import Platform
from spencerassistant.core import spencerAssistant
from spencerassistant.helpers import aiohttp_client, config_entry_oauth2_flow

from . import api
from .const import DOMAIN

# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
PLATFORMS: list[Platform] = [Platform.LIGHT]


async def async_setup_entry(hass: spencerAssistant, entry: ConfigEntry) -> bool:
    """Set up NEW_NAME from a config entry."""
    implementation = (
        await config_entry_oauth2_flow.async_get_config_entry_implementation(
            hass, entry
        )
    )

    session = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)

    # If using a requests-based API lib
    hass.data[DOMAIN][entry.entry_id] = api.ConfigEntryAuth(hass, session)

    # If using an aiohttp-based API lib
    hass.data[DOMAIN][entry.entry_id] = api.AsyncConfigEntryAuth(
        aiohttp_client.async_get_clientsession(hass), session
    )

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: spencerAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
