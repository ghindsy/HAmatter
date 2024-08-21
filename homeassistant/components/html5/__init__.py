"""The html5 component."""

import logging

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import CONF_PLATFORM, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, discovery
from homeassistant.helpers.typing import ConfigType

from .const import DATA_HASS_CONFIG, DOMAIN
from .issues import async_create_html5_issue

_LOGGER = logging.getLogger(__name__)

PLATFORM = Platform.NOTIFY
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the HTML5 push notification component."""
    hass.data[DATA_HASS_CONFIG] = config
    existing_config_entry = hass.config_entries.async_entries(DOMAIN)

    # Iterate all entries for notify to only get HTML5
    for entry in config.get(Platform.NOTIFY, {}):
        if entry[CONF_PLATFORM] != DOMAIN:
            continue
        # the configuration has already been imported
        # but the YAML configuration is still present
        if existing_config_entry:
            async_create_html5_issue(hass, True)
            return True
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_IMPORT}, data=entry
            )
        )
        return True
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HTML5 from a config entry."""
    hass.async_create_task(
        discovery.async_load_platform(
            hass, Platform.NOTIFY, DOMAIN, dict(entry.data), hass.data[DATA_HASS_CONFIG]
        )
    )
    return True
