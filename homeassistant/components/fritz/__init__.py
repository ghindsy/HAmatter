"""Support for AVM Fritz!Box functions."""
import logging

from fritzconnection.core.exceptions import FritzConnectionException, FritzSecurityError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import device_registry
from homeassistant.helpers.typing import ConfigType

from .common import FritzBoxTools, FritzData
from .const import DATA_FRITZ, DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up fritzboxtools from config entry."""
    _LOGGER.debug("Setting up FRITZ!Box Tools component")
    fritz_tools = FritzBoxTools(
        hass=hass,
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
    )

    try:
        await fritz_tools.async_setup()
        await fritz_tools.async_start()
    except FritzSecurityError as ex:
        raise ConfigEntryAuthFailed from ex
    except FritzConnectionException as ex:
        raise ConfigEntryNotReady from ex

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = fritz_tools

    if DATA_FRITZ not in hass.data:
        hass.data[DATA_FRITZ] = FritzData()

    @callback
    def _async_unload(event):
        fritz_tools.async_unload()

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _async_unload)
    )

    async_device_setup(hass, entry, fritz_tools)

    # Load the other platforms like switch
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


@callback
def async_device_setup(
    hass: HomeAssistant, entry: ConfigEntry, fritz_tools: FritzBoxTools
):
    """Set up a device that is online."""
    dev_reg = device_registry.async_get(hass)
    dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        name=entry.title,
        connections={(device_registry.CONNECTION_NETWORK_MAC, fritz_tools.mac)},
        # This is duplicate but otherwise via_device can't work
        identifiers={(DOMAIN, fritz_tools.mac)},
        manufacturer="AVM",
        model=fritz_tools._model,
        sw_version=fritz_tools._sw_version,
    )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigType) -> bool:
    """Unload FRITZ!Box Tools config entry."""
    fritzbox: FritzBoxTools = hass.data[DOMAIN][entry.entry_id]
    fritzbox.async_unload()

    fritz_data = hass.data[DATA_FRITZ]
    fritz_data.tracked.pop(fritzbox.unique_id)

    if not bool(fritz_data.tracked):
        hass.data.pop(DATA_FRITZ)

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
