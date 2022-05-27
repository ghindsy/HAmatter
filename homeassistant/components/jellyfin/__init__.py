"""The Jellyfin integration."""
import logging
import uuid

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .client_wrapper import CannotConnect, InvalidAuth, create_client, validate_input
from .const import DATA_CLIENT, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version == 1:
        unique_id = str(uuid.uuid4())
        hass.config_entries.async_update_entry(config_entry, unique_id=unique_id)
        config_entry.version = 2

    _LOGGER.debug("Migration to version %s successful", config_entry.version)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Jellyfin from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    assert entry.unique_id is not None

    client = create_client(entry.unique_id)
    try:
        await validate_input(hass, dict(entry.data), client)
    except CannotConnect as ex:
        raise ConfigEntryNotReady("Cannot connect to Jellyfin server") from ex
    except InvalidAuth:
        _LOGGER.error("Failed to login to Jellyfin server")
        return False
    else:
        hass.data[DOMAIN][entry.entry_id] = {DATA_CLIENT: client}

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    hass.data[DOMAIN].pop(entry.entry_id)

    return True
