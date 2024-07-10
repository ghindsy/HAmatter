"""The emoncms component."""

from pyemoncms import EmoncmsClient

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_URL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_MESSAGE, CONF_SUCCESS, DOMAIN, LOGGER
from .coordinator import EmoncmsCoordinator

PLATFORMS: list[str] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Load a config entry."""
    emoncms_client = EmoncmsClient(
        entry.data[CONF_URL],
        entry.data[CONF_API_KEY],
        session=async_get_clientsession(hass),
    )
    result = await emoncms_client.async_request("/feed/list.json")
    LOGGER.debug(result)
    if not result[CONF_SUCCESS]:
        raise ConfigEntryNotReady(result[CONF_MESSAGE])
    coordinator = EmoncmsCoordinator(hass, emoncms_client)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    entry.async_on_unload(entry.add_update_listener(update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    LOGGER.debug(f"reloading config entry {entry.entry_id} {entry.data}")
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
