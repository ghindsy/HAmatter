"""Tracks the latency of a host by sending ICMP echo requests (ping)."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.binary_sensor import (
    PLATFORM_SCHEMA as PARENT_PLATFORM_SCHEMA,
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import DOMAIN as HOMEASSISTANT_DOMAIN, HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.issue_registry import IssueSeverity, async_create_issue
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import PingDomainData, PingUpdateCoordinator
from .const import (
    CONF_IMPORTED_BY,
    CONF_PING_COUNT,
    DEFAULT_PING_COUNT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

ATTR_ROUND_TRIP_TIME_AVG = "round_trip_time_avg"
ATTR_ROUND_TRIP_TIME_MAX = "round_trip_time_max"
ATTR_ROUND_TRIP_TIME_MDEV = "round_trip_time_mdev"
ATTR_ROUND_TRIP_TIME_MIN = "round_trip_time_min"

PLATFORM_SCHEMA = PARENT_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_NAME): cv.string,
        vol.Optional(CONF_PING_COUNT, default=DEFAULT_PING_COUNT): vol.Range(
            min=1, max=100
        ),
    }
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Legacy init: Trigger the import config flow and create a deprecated yaml issue."""

    async_create_issue(
        hass,
        HOMEASSISTANT_DOMAIN,
        f"deprecated_yaml_{DOMAIN}",
        breaks_in_ha_version="2024.1.0",
        is_fixable=False,
        issue_domain=DOMAIN,
        severity=IssueSeverity.WARNING,
        translation_key="deprecated_yaml",
        translation_placeholders={
            "domain": DOMAIN,
            "integration_title": "Ping",
        },
    )

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data={CONF_IMPORTED_BY: "binary_sensor", **config},
        )
    )


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a Ping config entry."""

    data: PingDomainData = hass.data[DOMAIN]

    name: str = entry.options[CONF_NAME]
    coordinator: PingUpdateCoordinator = data.coordinators[entry.entry_id]

    async_add_entities([PingBinarySensor(name, entry, coordinator)])


class PingBinarySensor(CoordinatorEntity[PingUpdateCoordinator], BinarySensorEntity):
    """Representation of a Ping Binary sensor."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    config_entry: ConfigEntry

    def __init__(
        self, name: str, config_entry: ConfigEntry, coordinator: PingUpdateCoordinator
    ) -> None:
        """Initialize the Ping binary sensor."""
        super().__init__(coordinator)

        self._attr_name = name
        self._attr_unique_id = f"{config_entry.entry_id}_binary_sensor"
        self.config_entry = config_entry

    @property
    def is_on(self) -> bool:
        """Return true if the host is available."""
        return self.coordinator.data.is_alive

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the state attributes of the ICMP echo request."""
        if self.coordinator.data.data is None:
            return None
        return {
            ATTR_ROUND_TRIP_TIME_AVG: self.coordinator.data.data["avg"],
            ATTR_ROUND_TRIP_TIME_MAX: self.coordinator.data.data["max"],
            ATTR_ROUND_TRIP_TIME_MDEV: self.coordinator.data.data["mdev"],
            ATTR_ROUND_TRIP_TIME_MIN: self.coordinator.data.data["min"],
        }

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if entity is enabled by default."""
        if CONF_IMPORTED_BY in self.config_entry.options:
            return bool(self.config_entry.options[CONF_IMPORTED_BY] == "binary_sensor")
        return True
