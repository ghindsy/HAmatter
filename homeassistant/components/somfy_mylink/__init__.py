"""Component for the Somfy MyLink device supporting the Synergy API."""
import asyncio
import logging

from somfy_mylink_synergy import SomfyMyLinkSynergy
import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_DEFAULT_REVERSE,
    CONF_ENTITY_CONFIG,
    CONF_REVERSE,
    CONF_SYSTEM_ID,
    DATA_SOMFY_MYLINK,
    DEFAULT_PORT,
    DOMAIN,
    MYLINK_ENTITY_IDS,
    MYLINK_STATUS,
    SOMFY_MYLINK_COMPONENTS,
)

CONFIG_OPTIONS = (CONF_DEFAULT_REVERSE, CONF_ENTITY_CONFIG)
UNDO_UPDATE_LISTENER = "undo_update_listener"

_LOGGER = logging.getLogger(__name__)


def validate_entity_config(values):
    """Validate config entry for CONF_ENTITY."""
    entity_config_schema = vol.Schema({vol.Optional(CONF_REVERSE): cv.boolean})
    if not isinstance(values, dict):
        raise vol.Invalid("expected a dictionary")
    entities = {}
    for entity_id, config in values.items():
        entity = cv.entity_id(entity_id)
        config = entity_config_schema(config)
        entities[entity] = config
    return entities


CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_SYSTEM_ID): cv.string,
                vol.Required(CONF_HOST): cv.string,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
                vol.Optional(CONF_DEFAULT_REVERSE, default=False): cv.boolean,
                vol.Optional(CONF_ENTITY_CONFIG, default={}): validate_entity_config,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass, config):
    """Set up the MyLink platform."""

    conf = config.get(DOMAIN)
    hass.data.setdefault(DOMAIN, {})

    if not conf:
        return True

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_IMPORT}, data=conf
        )
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Somfy MyLink from a config entry."""
    _async_import_options_from_data_if_missing(hass, entry)

    config = entry.data
    host = config[CONF_HOST]
    port = config[CONF_PORT]
    system_id = config[CONF_SYSTEM_ID]

    somfy_mylink = SomfyMyLinkSynergy(system_id, host, port)

    try:
        mylink_status = await somfy_mylink.status_info()
    except asyncio.TimeoutError:
        raise ConfigEntryNotReady(
            "Unable to connect to the Somfy MyLink device, please check your settings"
        )

    _LOGGER.warning("Entry loading for mylink")
    undo_listener = entry.add_update_listener(_async_update_listener)

    hass.data[DOMAIN][entry.entry_id] = {
        DATA_SOMFY_MYLINK: somfy_mylink,
        MYLINK_STATUS: mylink_status,
        MYLINK_ENTITY_IDS: [],
        UNDO_UPDATE_LISTENER: undo_listener,
    }

    for component in SOMFY_MYLINK_COMPONENTS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


@callback
def _async_import_options_from_data_if_missing(hass: HomeAssistant, entry: ConfigEntry):
    options = dict(entry.options)
    data = dict(entry.data)
    modified = False
    for importable_option in CONFIG_OPTIONS:
        if importable_option not in options and importable_option in data:
            options[importable_option] = data.pop(importable_option)
            modified = True

    if modified:
        hass.config_entries.async_update_entry(entry, data=data, options=options)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in SOMFY_MYLINK_COMPONENTS
            ]
        )
    )

    hass.data[DOMAIN][entry.entry_id][UNDO_UPDATE_LISTENER]()

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
