"""Support for an Intergas boiler via an InComfort/Intouch Lan2RF gateway."""

from __future__ import annotations

import logging

from aiohttp import ClientResponseError
from incomfortclient import IncomfortError, InvalidHeaterList
import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import DOMAIN as HOMEASSISTANT_DOMAIN, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import config_validation as cv, issue_registry as ir
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .errors import InConfortTimeout, InConfortUnknownError, NoHeaters, NotFound
from .models import DATA_INCOMFORT, async_connect_gateway

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_HOST): cv.string,
                vol.Inclusive(CONF_USERNAME, "credentials"): cv.string,
                vol.Inclusive(CONF_PASSWORD, "credentials"): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

PLATFORMS = (
    Platform.WATER_HEATER,
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.CLIMATE,
)


async def async_setup(hass: HomeAssistant, hass_config: ConfigType) -> bool:
    """Create an Intergas InComfort/Intouch system."""

    if config := hass_config.get(DOMAIN):
        ir.async_create_issue(
            hass,
            HOMEASSISTANT_DOMAIN,
            f"deprecated_yaml_{DOMAIN}",
            breaks_in_ha_version="2025.1.0",
            is_fixable=False,
            issue_domain=DOMAIN,
            severity=ir.IssueSeverity.WARNING,
            translation_key="deprecated_yaml",
            translation_placeholders={
                "domain": DOMAIN,
                "integration_title": "Intergas InComfort/Intouch Lan2RF gateway",
            },
        )

    if hass.config_entries.async_entries(DOMAIN):
        return True
    # Start import flow
    if config:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_IMPORT}, data=config
            )
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry."""
    try:
        data = await async_connect_gateway(hass, dict(entry.data))
    except InvalidHeaterList as exc:
        raise NoHeaters from exc
    except IncomfortError as exc:
        if isinstance(exc.message, ClientResponseError):
            if exc.message.status == 401:
                raise ConfigEntryAuthFailed("Incorrect credentials") from exc
            if exc.message.status == 404:
                raise NotFound from exc
        raise InConfortUnknownError from exc
    except TimeoutError as exc:
        raise InConfortTimeout from exc
    except Exception as exc:  # noqa: BLE001
        raise InConfortUnknownError from exc

    hass.data.setdefault(DATA_INCOMFORT, {entry.entry_id: data})
    for heater in data.heaters:
        await heater.update()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    del hass.data[DOMAIN][entry.entry_id]
    return unload_ok


class IncomfortEntity(Entity):
    """Base class for all InComfort entities."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    async def async_added_to_hass(self) -> None:
        """Set up a listener when this entity is added to HA."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, f"{DOMAIN}_{self.unique_id}", self._refresh
            )
        )

    @callback
    def _refresh(self) -> None:
        self.async_schedule_update_ha_state(force_refresh=True)
