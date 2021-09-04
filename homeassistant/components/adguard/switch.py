"""Support for AdGuard Home switches."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from adguardhome import AdGuardHome, AdGuardHomeConnectionError, AdGuardHomeError
import voluptuous as vol

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_URL
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AdGuardHomeDeviceEntity
from .const import (
    CONF_FORCE,
    DATA_ADGUARD_CLIENT,
    DATA_ADGUARD_VERSION,
    DOMAIN,
    SERVICE_ADD_URL,
    SERVICE_DISABLE_URL,
    SERVICE_ENABLE_URL,
    SERVICE_REFRESH,
    SERVICE_REMOVE_URL,
)

SERVICE_URL_SCHEMA = cv.make_entity_service_schema({vol.Required(CONF_URL): cv.url})
SERVICE_ADD_URL_SCHEMA = cv.make_entity_service_schema(
    {vol.Required(CONF_NAME): cv.string, vol.Required(CONF_URL): cv.url}
)
SERVICE_REFRESH_SCHEMA = cv.make_entity_service_schema(
    {vol.Optional(CONF_FORCE, default=False): cv.boolean}
)

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=10)
PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AdGuard Home switch based on a config entry."""
    platform = entity_platform.async_get_current_platform()

    adguard = hass.data[DOMAIN][entry.entry_id][DATA_ADGUARD_CLIENT]

    try:
        version = await adguard.version()
    except AdGuardHomeConnectionError as exception:
        raise PlatformNotReady from exception

    hass.data[DOMAIN][entry.entry_id][DATA_ADGUARD_VERSION] = version

    switches = [
        AdGuardHomeProtectionSwitch(adguard, entry),
        AdGuardHomeFilteringSwitch(adguard, entry),
        AdGuardHomeParentalSwitch(adguard, entry),
        AdGuardHomeSafeBrowsingSwitch(adguard, entry),
        AdGuardHomeSafeSearchSwitch(adguard, entry),
        AdGuardHomeQueryLogSwitch(adguard, entry),
    ]
    async_add_entities(switches, True)

    async def async_service_handle(service_call: ServiceCall) -> None:
        """Handle dispatched services."""
        assert platform is not None
        entities = await platform.async_extract_from_service(service_call)

        adguard_instances = []
        for entity in entities:
            assert isinstance(entity, AdGuardHomeDeviceEntity)
            adguard_instances.append(entity.adguard)
        for adguard_instance in set(adguard_instances):
            if service_call.service == SERVICE_ADD_URL:
                await add_url(adguard_instance, service_call)
            if service_call.service == SERVICE_REMOVE_URL:
                await remove_url(adguard_instance, service_call)
            if service_call.service == SERVICE_ENABLE_URL:
                await enable_url(adguard_instance, service_call)
            if service_call.service == SERVICE_DISABLE_URL:
                await disable_url(adguard_instance, service_call)
            if service_call.service == SERVICE_REFRESH:
                await refresh(adguard_instance, service_call)

    async def add_url(adguard: AdGuardHome, service_call: ServiceCall) -> None:
        """Service call to add a new filter subscription to AdGuard Home."""
        await adguard.filtering.add_url(
            allowlist=False,
            name=str(service_call.data.get(CONF_NAME)),
            url=str(service_call.data.get(CONF_URL)),
        )

    async def remove_url(adguard: AdGuardHome, service_call: ServiceCall) -> None:
        """Service call to remove a filter subscription from AdGuard Home."""
        await adguard.filtering.remove_url(
            allowlist=False, url=str(service_call.data.get(CONF_URL))
        )

    async def enable_url(adguard: AdGuardHome, service_call: ServiceCall) -> None:
        """Service call to enable a filter subscription in AdGuard Home."""
        await adguard.filtering.enable_url(
            allowlist=False, url=str(service_call.data.get(CONF_URL))
        )

    async def disable_url(adguard: AdGuardHome, service_call: ServiceCall) -> None:
        """Service call to disable a filter subscription in AdGuard Home."""
        await adguard.filtering.disable_url(
            allowlist=False, url=str(service_call.data.get(CONF_URL))
        )

    async def refresh(adguard: AdGuardHome, service_call: ServiceCall) -> None:
        """Service call to refresh the filter subscriptions in AdGuard Home."""
        await adguard.filtering.refresh(
            allowlist=False, force=service_call.data.get(CONF_FORCE, False)
        )

    hass.services.async_register(
        DOMAIN, SERVICE_ADD_URL, async_service_handle, SERVICE_ADD_URL_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_REMOVE_URL, async_service_handle, SERVICE_URL_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_ENABLE_URL, async_service_handle, SERVICE_URL_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_DISABLE_URL, async_service_handle, SERVICE_URL_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_REFRESH, async_service_handle, SERVICE_REFRESH_SCHEMA
    )


class AdGuardHomeSwitch(AdGuardHomeDeviceEntity, SwitchEntity):
    """Defines a AdGuard Home switch."""

    def __init__(
        self,
        adguard: AdGuardHome,
        entry: ConfigEntry,
        name: str,
        icon: str,
        key: str,
        enabled_default: bool = True,
    ) -> None:
        """Initialize AdGuard Home switch."""
        self._state = False
        self._key = key
        super().__init__(adguard, entry, name, icon, enabled_default)

    @property
    def unique_id(self) -> str:
        """Return the unique ID for this sensor."""
        return "_".join(
            [DOMAIN, self.adguard.host, str(self.adguard.port), "switch", self._key]
        )

    @property
    def is_on(self) -> bool:
        """Return the state of the switch."""
        return self._state

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch."""
        try:
            await self._adguard_turn_off()
        except AdGuardHomeError:
            _LOGGER.error("An error occurred while turning off AdGuard Home switch")
            self._available = False

    async def _adguard_turn_off(self) -> None:
        """Turn off the switch."""
        raise NotImplementedError()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch."""
        try:
            await self._adguard_turn_on()
        except AdGuardHomeError:
            _LOGGER.error("An error occurred while turning on AdGuard Home switch")
            self._available = False

    async def _adguard_turn_on(self) -> None:
        """Turn on the switch."""
        raise NotImplementedError()


class AdGuardHomeProtectionSwitch(AdGuardHomeSwitch):
    """Defines a AdGuard Home protection switch."""

    def __init__(self, adguard: AdGuardHome, entry: ConfigEntry) -> None:
        """Initialize AdGuard Home switch."""
        super().__init__(
            adguard, entry, "AdGuard Protection", "mdi:shield-check", "protection"
        )

    async def _adguard_turn_off(self) -> None:
        """Turn off the switch."""
        await self.adguard.disable_protection()

    async def _adguard_turn_on(self) -> None:
        """Turn on the switch."""
        await self.adguard.enable_protection()

    async def _adguard_update(self) -> None:
        """Update AdGuard Home entity."""
        self._state = await self.adguard.protection_enabled()


class AdGuardHomeParentalSwitch(AdGuardHomeSwitch):
    """Defines a AdGuard Home parental control switch."""

    def __init__(self, adguard: AdGuardHome, entry: ConfigEntry) -> None:
        """Initialize AdGuard Home switch."""
        super().__init__(
            adguard, entry, "AdGuard Parental Control", "mdi:shield-check", "parental"
        )

    async def _adguard_turn_off(self) -> None:
        """Turn off the switch."""
        await self.adguard.parental.disable()

    async def _adguard_turn_on(self) -> None:
        """Turn on the switch."""
        await self.adguard.parental.enable()

    async def _adguard_update(self) -> None:
        """Update AdGuard Home entity."""
        self._state = await self.adguard.parental.enabled()


class AdGuardHomeSafeSearchSwitch(AdGuardHomeSwitch):
    """Defines a AdGuard Home safe search switch."""

    def __init__(self, adguard: AdGuardHome, entry: ConfigEntry) -> None:
        """Initialize AdGuard Home switch."""
        super().__init__(
            adguard, entry, "AdGuard Safe Search", "mdi:shield-check", "safesearch"
        )

    async def _adguard_turn_off(self) -> None:
        """Turn off the switch."""
        await self.adguard.safesearch.disable()

    async def _adguard_turn_on(self) -> None:
        """Turn on the switch."""
        await self.adguard.safesearch.enable()

    async def _adguard_update(self) -> None:
        """Update AdGuard Home entity."""
        self._state = await self.adguard.safesearch.enabled()


class AdGuardHomeSafeBrowsingSwitch(AdGuardHomeSwitch):
    """Defines a AdGuard Home safe search switch."""

    def __init__(self, adguard: AdGuardHome, entry: ConfigEntry) -> None:
        """Initialize AdGuard Home switch."""
        super().__init__(
            adguard, entry, "AdGuard Safe Browsing", "mdi:shield-check", "safebrowsing"
        )

    async def _adguard_turn_off(self) -> None:
        """Turn off the switch."""
        await self.adguard.safebrowsing.disable()

    async def _adguard_turn_on(self) -> None:
        """Turn on the switch."""
        await self.adguard.safebrowsing.enable()

    async def _adguard_update(self) -> None:
        """Update AdGuard Home entity."""
        self._state = await self.adguard.safebrowsing.enabled()


class AdGuardHomeFilteringSwitch(AdGuardHomeSwitch):
    """Defines a AdGuard Home filtering switch."""

    def __init__(self, adguard: AdGuardHome, entry: ConfigEntry) -> None:
        """Initialize AdGuard Home switch."""
        super().__init__(
            adguard, entry, "AdGuard Filtering", "mdi:shield-check", "filtering"
        )

    async def _adguard_turn_off(self) -> None:
        """Turn off the switch."""
        await self.adguard.filtering.disable()

    async def _adguard_turn_on(self) -> None:
        """Turn on the switch."""
        await self.adguard.filtering.enable()

    async def _adguard_update(self) -> None:
        """Update AdGuard Home entity."""
        self._state = await self.adguard.filtering.enabled()


class AdGuardHomeQueryLogSwitch(AdGuardHomeSwitch):
    """Defines a AdGuard Home query log switch."""

    def __init__(self, adguard: AdGuardHome, entry: ConfigEntry) -> None:
        """Initialize AdGuard Home switch."""
        super().__init__(
            adguard,
            entry,
            "AdGuard Query Log",
            "mdi:shield-check",
            "querylog",
            enabled_default=False,
        )

    async def _adguard_turn_off(self) -> None:
        """Turn off the switch."""
        await self.adguard.querylog.disable()

    async def _adguard_turn_on(self) -> None:
        """Turn on the switch."""
        await self.adguard.querylog.enable()

    async def _adguard_update(self) -> None:
        """Update AdGuard Home entity."""
        self._state = await self.adguard.querylog.enabled()
