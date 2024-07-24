"""The onkyo component."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from . import receiver as rcver
from .const import DOMAIN

PLATFORMS = [Platform.MEDIA_PLAYER]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type OnkyoConfigEntry = ConfigEntry[rcver.Receiver]


async def async_setup(hass: HomeAssistant, _: ConfigType) -> bool:
    """Set up Onkyo component."""
    # pylint: disable-next=import-outside-toplevel
    from .media_player import async_register_services

    await async_register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: OnkyoConfigEntry) -> bool:
    """Set up the Onkyo config entry."""
    entry.async_on_unload(entry.add_update_listener(update_listener))

    host = entry.data[CONF_HOST]

    info = await rcver.async_interview(host)
    if info is None:
        raise ConfigEntryNotReady(f"Unable to connect to : {host}")

    receiver = await rcver.async_setup(info)

    entry.runtime_data = receiver

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    await receiver.connect()

    return True


async def async_unload_entry(hass: HomeAssistant, entry: OnkyoConfigEntry) -> bool:
    """Unload Onkyo config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    receiver = entry.runtime_data
    receiver.close()

    return unload_ok


async def update_listener(hass: HomeAssistant, entry: OnkyoConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
