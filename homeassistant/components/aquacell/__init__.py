"""The Aquacell integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aioaquacell import AquacellApi
from aioaquacell.const import Brand

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_BRAND
from .coordinator import AquacellCoordinator

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

PLATFORMS = [Platform.SENSOR]

type AquacellConfigEntry = ConfigEntry[AquacellCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: AquacellConfigEntry) -> bool:
    """Set up Aquacell from a config entry."""
    session = async_get_clientsession(hass)

    brand = entry.data.get(CONF_BRAND, Brand.AQUACELL)

    aquacell_api = AquacellApi(session, brand)

    coordinator = AquacellCoordinator(hass, aquacell_api)

    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
