from __future__ import annotations

from nextcloudmonitor import NextcloudMonitorError, NextcloudMonitor

import logging
from aiohttp import BasicAuth
import voluptuous as vol
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_URL,
    CONF_USERNAME,
    CONF_NAME,
    CONF_LOCATION,
    CONF_VERIFY_SSL,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    DATA_KEY_API,
    DATA_KEY_COORDINATOR,
    DEFAULT_NAME,
    SCAN_INTERVAL,
    DOMAIN,
)

from .const import DOMAIN

NEXTCLOUD_SCHEMA = vol.Schema(
    vol.All(
        {
            vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
            vol.Required(CONF_URL): cv.string,
            vol.Optional(CONF_USERNAME): cv.string,
            vol.Optional(CONF_PASSWORD): cv.string,
            vol.Optional(CONF_LOCATION): cv.string,
            vol.Optional(CONF_VERIFY_SSL, default=True): cv.boolean,
        },
    )
)

CONFIG_SCHEMA = vol.Schema(
    vol.All(
        cv.deprecated(DOMAIN),
        {DOMAIN: vol.Schema(vol.All(cv.ensure_list, [NEXTCLOUD_SCHEMA]))},
    ),
    extra=vol.ALLOW_EXTRA,
)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]


class NextcloudMonitorWrapper:
    """An object containing a dictionary representation of dat returned by
    Nextcloud's monitoring api

    Attributes:
        nextcloud_url (str): Full https url to a nextcloud instance
        user (str): Username of the Nextcloud user with access to the monitor api
        app_password (str): App password generated from Nextcloud security settings page
        verify_ssl (bool): Allow bypassing ssl verification, but verify by default
    """

    def __init__(self, url: str, user: str, app_password: str, verify_ssl: bool):
        self.data = dict()
        self.url = url
        self.user = user
        self.password = app_password
        self.verify_ssl = verify_ssl
        self.create_api()

    def create_api(self) -> None:
        self.api = NextcloudMonitor(self.url, self.user, self.password, self.verify_ssl)
        self.data = self.get_data_points(self.api.data)

    def get_data_points(self, api_data: dict, key_path="", leaf=False) -> dict:
        """Use Recursion to discover data-points and values.

        Get dictionary of data-points by recursing through dict returned by api until
        the dictionary value does not contain another dictionary and use the
        resulting path of dictionary keys and resulting value as the name/value
        for the data-point.

        returns: dictionary of data-point/values
        """
        result = {}
        for key, value in api_data.items():
            if isinstance(value, dict):
                if leaf:
                    key_path = f"{key}_"
                if not leaf:
                    key_path += f"{key}_"
                leaf = True
                result.update(self.get_data_points(value, key_path, leaf))
            else:
                result[f"{key_path}{key}"] = value
                leaf = False
        return result

    def update(self) -> None:
        self.api.update()
        self.data = self.get_data_points(self.api.data)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Pi-hole integration."""

    hass.data[DOMAIN] = {}
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ABB Power-One PVI SunSpec"""
    url = entry.data[CONF_URL]
    name = entry.data[CONF_NAME]
    user = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    verify_ssl = entry.data[CONF_VERIFY_SSL]

    _LOGGER.debug("Setup %s.%s", DOMAIN, name)

    try:
        # session = async_get_clientsession(hass, verify_ssl)
        # ncm = NextcloudMonitorCustom(url, user, password, session=session)
        # await ncm.async_update()
        ncmw = await hass.async_add_executor_job(
            NextcloudMonitorWrapper, url, user, password, verify_ssl
        )

        # await hass.async_add_executor_job( NextcloudMonitor(url, user, password) )
    except NextcloudMonitorError as ex:
        _LOGGER.warning("Nextcloud setup failed - Check configuration")
        raise ConfigEntryNotReady from ex

    # async def async_update_data() -> None:
    #    """Update data from nextcloud api."""
    #    try:
    #        await ncm.async_update()
    #        _LOGGER.error("Updating NC API")
    #    except NextcloudMonitorError:
    #        _LOGGER.error("Nextcloud update failed")
    #        return False

    async def async_update_data() -> None:
        """Update data from nextcloud api."""
        try:
            await hass.async_add_executor_job(ncmw.update)
            _LOGGER.info("Updating NC API")
        except NextcloudMonitorError:
            _LOGGER.error("Nextcloud update failed")
            return False

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=name,
        update_method=async_update_data,
        update_interval=SCAN_INTERVAL,
    )

    hass.data[DOMAIN][name] = {
        DATA_KEY_API: ncmw,
        DATA_KEY_COORDINATOR: coordinator,
    }

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )
    return True


class NextcloudEntity(CoordinatorEntity):
    """Representation of a Pi-hole entity."""

    def __init__(
        self,
        api: NextcloudMonitorWrapper,
        coordinator: DataUpdateCoordinator,
        name: str,
        server_unique_id: str,
    ) -> None:
        """Initialize a Pi-hole entity."""
        super().__init__(coordinator)
        self.api = api
        self._name = name
        self._server_unique_id = server_unique_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device information of the entity."""

        return DeviceInfo(
            identifiers={(DOMAIN, self._server_unique_id)},
            name=self._name,
            manufacturer="NextCloud",
            configuration_url=self.api.url,
        )
