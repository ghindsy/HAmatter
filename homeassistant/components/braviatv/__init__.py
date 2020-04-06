"""The Bravia TV component."""
import asyncio

from bravia_tv import BraviaRC

from homeassistant.const import CONF_HOST, CONF_PIN
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CLIENTID_PREFIX, DOMAIN, NICKNAME

PLATFORMS = ["media_player"]


async def async_setup(hass, config):
    """Set up the Bravia TV component."""
    return True


async def async_setup_entry(hass, config_entry):
    """Set up a config entry."""
    host = config_entry.data[CONF_HOST]
    pin = config_entry.data[CONF_PIN]

    braviarc = BraviaRC(host)

    await hass.async_add_executor_job(braviarc.connect, pin, CLIENTID_PREFIX, NICKNAME)

    if not braviarc.is_connected():
        raise ConfigEntryNotReady

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = braviarc

    config_entry.add_update_listener(update_listener)

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(config_entry, component)
        )

    return True


async def async_unload_entry(hass, config_entry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(config_entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)

    return unload_ok


async def update_listener(hass, config_entry):
    """Handle an options update."""
    for component in PLATFORMS:
        await hass.config_entries.async_forward_entry_unload(config_entry, component)
    hass.async_add_job(async_setup_entry(hass, config_entry))
