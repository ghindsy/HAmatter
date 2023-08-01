"""Tracks devices by sending a ICMP echo request (ping)."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.components.device_tracker import (
    PLATFORM_SCHEMA as BASE_PLATFORM_SCHEMA,
    AsyncSeeCallback,
    ScannerEntity,
    SourceType,
)
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import CONF_HOST, CONF_HOSTS, CONF_NAME
from homeassistant.core import DOMAIN as HOMEASSISTANT_DOMAIN, HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.issue_registry import IssueSeverity, async_create_issue
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import PingDomainData
from .const import (
    CONF_IMPORTED_BY,
    CONF_PING_COUNT,
    DOMAIN,
)
from .coordinator import PingUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = BASE_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOSTS): {cv.slug: cv.string},
        vol.Optional(CONF_PING_COUNT, default=1): cv.positive_int,
    }
)


async def async_setup_scanner(
    hass: HomeAssistant,
    config: ConfigType,
    async_see: AsyncSeeCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> bool:
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

    for dev_name, dev_host in config[CONF_HOSTS].items():
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_IMPORT},
                data={
                    CONF_IMPORTED_BY: "device_tracker",
                    CONF_NAME: dev_name,
                    CONF_HOST: dev_host,
                    CONF_PING_COUNT: config[CONF_PING_COUNT],
                },
            )
        )

    return True


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a Ping device_tracker config entry."""

    data: PingDomainData = hass.data[DOMAIN]

    name: str = config_entry.options[CONF_NAME]
    coordinator: PingUpdateCoordinator = data.coordinators[config_entry.entry_id]

    async_add_entities([PingDeviceTracker(name, config_entry, coordinator)])


class PingDeviceTracker(CoordinatorEntity[PingUpdateCoordinator], ScannerEntity):
    """Representation of a Ping device tracker."""

    _attr_should_poll = False
    config_entry: ConfigEntry

    def __init__(
        self, name: str, config_entry: ConfigEntry, coordinator: PingUpdateCoordinator
    ) -> None:
        """Initialize the Ping device tracker."""
        super().__init__(coordinator)

        self._attr_name = name
        self._unique_id = f"{config_entry.entry_id}_device_tracker"
        self.coordinator = coordinator
        self.config_entry = config_entry

    @property
    def unique_id(self) -> str:
        """Return unique ID of the entity."""
        return self._unique_id

    @property
    def source_type(self) -> SourceType:
        """Return the source type which is router."""
        return SourceType.ROUTER

    @property
    def is_connected(self) -> bool:
        """Return true if ping returns is_alive."""
        return self.coordinator.data.is_alive

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if entity is enabled by default."""
        if CONF_IMPORTED_BY in self.config_entry.options:
            return bool(self.config_entry.options[CONF_IMPORTED_BY] == "device_tracker")
        return False
