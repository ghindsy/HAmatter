"""Support for tracking the proximity of a device."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    CONF_DEVICES,
    CONF_NAME,
    CONF_UNIT_OF_MEASUREMENT,
    CONF_ZONE,
    Platform,
)
from homeassistant.core import DOMAIN as HOMEASSISTANT_DOMAIN, HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import (
    async_track_entity_registry_updated_event,
    async_track_state_change_event,
)
from homeassistant.helpers.issue_registry import IssueSeverity, async_create_issue
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_IGNORED_ZONES,
    CONF_TOLERANCE,
    CONF_TRACKED_ENTITIES,
    DEFAULT_PROXIMITY_ZONE,
    DEFAULT_TOLERANCE,
    DOMAIN,
    UNITS,
)
from .coordinator import ProximityConfigEntry, ProximityDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

ZONE_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_ZONE, default=DEFAULT_PROXIMITY_ZONE): cv.string,
        vol.Optional(CONF_DEVICES, default=[]): vol.All(cv.ensure_list, [cv.entity_id]),
        vol.Optional(CONF_IGNORED_ZONES, default=[]): vol.All(
            cv.ensure_list, [cv.string]
        ),
        vol.Optional(CONF_TOLERANCE, default=DEFAULT_TOLERANCE): cv.positive_int,
        vol.Optional(CONF_UNIT_OF_MEASUREMENT): vol.All(cv.string, vol.In(UNITS)),
    }
)

CONFIG_SCHEMA = vol.Schema(
    vol.All(
        cv.deprecated(DOMAIN),
        {DOMAIN: cv.schema_with_slug_keys(ZONE_SCHEMA)},
    ),
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Get the zones and offsets from configuration.yaml."""
    if DOMAIN in config:
        for friendly_name, proximity_config in config[DOMAIN].items():
            _LOGGER.debug("import %s with config:%s", friendly_name, proximity_config)
            hass.async_create_task(
                hass.config_entries.flow.async_init(
                    DOMAIN,
                    context={"source": SOURCE_IMPORT},
                    data={
                        CONF_NAME: friendly_name,
                        CONF_ZONE: f"zone.{proximity_config[CONF_ZONE]}",
                        CONF_TRACKED_ENTITIES: proximity_config[CONF_DEVICES],
                        CONF_IGNORED_ZONES: [
                            f"zone.{zone}"
                            for zone in proximity_config[CONF_IGNORED_ZONES]
                        ],
                        CONF_TOLERANCE: proximity_config[CONF_TOLERANCE],
                        CONF_UNIT_OF_MEASUREMENT: proximity_config.get(
                            CONF_UNIT_OF_MEASUREMENT, hass.config.units.length_unit
                        ),
                    },
                )
            )

        async_create_issue(
            hass,
            HOMEASSISTANT_DOMAIN,
            f"deprecated_yaml_{DOMAIN}",
            breaks_in_ha_version="2024.8.0",
            is_fixable=False,
            issue_domain=DOMAIN,
            severity=IssueSeverity.WARNING,
            translation_key="deprecated_yaml",
            translation_placeholders={
                "domain": DOMAIN,
                "integration_title": "Proximity",
            },
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ProximityConfigEntry) -> bool:
    """Set up Proximity from a config entry."""
    _LOGGER.debug("setup %s with config:%s", entry.title, entry.data)

    coordinator = ProximityDataUpdateCoordinator(hass, entry.title, dict(entry.data))

    entry.async_on_unload(
        async_track_state_change_event(
            hass,
            entry.data[CONF_TRACKED_ENTITIES],
            coordinator.async_check_proximity_state_change,
        )
    )

    entry.async_on_unload(
        async_track_entity_registry_updated_event(
            hass,
            entry.data[CONF_TRACKED_ENTITIES],
            coordinator.async_check_tracked_entity_change,
        )
    )

    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, [Platform.SENSOR])


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
