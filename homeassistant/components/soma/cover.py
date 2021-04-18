"""Support for Soma Covers."""
import logging

from requests import RequestException

from homeassistant.components.cover import (
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    DEVICE_CLASS_BLIND,
    DEVICE_CLASS_SHADE,
    SUPPORT_CLOSE,
    SUPPORT_CLOSE_TILT,
    SUPPORT_OPEN,
    SUPPORT_OPEN_TILT,
    SUPPORT_SET_POSITION,
    SUPPORT_SET_TILT_POSITION,
    SUPPORT_STOP,
    SUPPORT_STOP_TILT,
    CoverEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import API, DEVICES, DOMAIN, SomaEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Soma cover platform."""

    devices = hass.data[DOMAIN][DEVICES]
    entities = []

    for device in devices:
        entities.append(SomaTilt(device, hass.data[DOMAIN][API]))

    async_add_entities(entities, True)


class SomaTilt(SomaEntity, CoverEntity):
    """Representation of a Soma Tilt device."""

    @property
    def device_class(self):
        """Return the class of this device."""
        return DEVICE_CLASS_BLIND

    @property
    def supported_features(self):
        """Flag supported features."""
        supported_features = (
            SUPPORT_OPEN_TILT
            | SUPPORT_CLOSE_TILT
            | SUPPORT_STOP_TILT
            | SUPPORT_SET_TILT_POSITION
        )
        return supported_features

    @property
    def current_cover_tilt_position(self):
        """Return the current cover tilt position."""
        return self.current_position

    @property
    def is_closed(self):
        """Return if the cover tilt is closed."""
        return self.current_position == 0

    def close_cover_tilt(self, **kwargs):
        """Close the cover tilt."""
        response = self.api.set_shade_position(self.device["mac"], 100)
        if response["result"] == "success":
            self.current_position = 0
        else:
            super().log_device_unreachable(
                _LOGGER, self.device["name"], response["msg"]
            )

    def open_cover_tilt(self, **kwargs):
        """Open the cover tilt."""
        response = self.api.set_shade_position(self.device["mac"], -100)
        if response["result"] == "success":
            self.current_position = 100
        else:
            super().log_device_unreachable(
                _LOGGER, self.device["name"], response["msg"]
            )

    def stop_cover_tilt(self, **kwargs):
        """Stop the cover tilt."""
        response = self.api.stop_shade(self.device["mac"])
        if response["result"] == "success":
            # Set cover position to some value where up/down are both enabled
            self.current_position = 50
        else:
            super().log_device_unreachable(
                _LOGGER, self.device["name"], response["msg"]
            )

    def set_cover_tilt_position(self, **kwargs):
        """Move the cover tilt to a specific position."""
        # 0 -> Closed down (api: 100)
        # 50 -> Fully open (api: 0)
        # 100 -> Closed up (api: -100)
        target_api_position = 100 - ((kwargs[ATTR_TILT_POSITION] / 50) * 100)
        response = self.api.set_shade_position(self.device["mac"], target_api_position)
        if response["result"] == "success":
            self.current_position = kwargs[ATTR_TILT_POSITION]
        else:
            super().log_device_unreachable(
                _LOGGER, self.device["name"], response["msg"]
            )

    async def async_update(self):
        """Update the entity with the latest data."""
        try:
            _LOGGER.debug("Soma Tilt Update")
            response = await self.hass.async_add_executor_job(
                self.api.get_shade_state, self.device["mac"]
            )
        except RequestException:
            _LOGGER.error("Connection to SOMA Connect failed")
            self.is_available = False
            return

        if response["result"] != "success":
            super().log_device_unreachable(
                _LOGGER, self.device["name"], response["msg"]
            )
            self.is_available = False
            return

        self.is_available = True
        api_position = response["position"]

        if "closed_upwards" in response.keys():
            self.current_position = 50 + ((api_position * 50) / 100)
        else:
            self.current_position = 50 - ((api_position * 50) / 100)


class SomaShade(SomaEntity, CoverEntity):
    """Representation of a Soma Shade device."""

    @property
    def device_class(self):
        """Return the class of this device."""
        return DEVICE_CLASS_SHADE

    @property
    def supported_features(self):
        """Flag supported features."""
        supported_features = (
            SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_STOP | SUPPORT_SET_POSITION
        )
        return supported_features

    @property
    def current_cover_position(self):
        """Return the current cover position."""
        return self.current_position

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        return self.current_position == 0

    def log_device_unreachable(self, name, msg):
        """Log device unreachable."""
        _LOGGER.error("Unable to reach device %s (%s)", name, msg)

    def close_cover(self, **kwargs):
        """Close the cover."""
        response = self.api.set_shade_position(self.device["mac"], 100)
        if response["result"] != "success":
            super().log_device_unreachable(
                _LOGGER, self.device["name"], response["msg"]
            )

    def open_cover(self, **kwargs):
        """Open the cover."""
        response = self.api.set_shade_position(self.device["mac"], 0)
        if response["result"] != "success":
            super().log_device_unreachable(
                _LOGGER, self.device["name"], response["msg"]
            )

    def stop_cover(self, **kwargs):
        """Stop the cover."""
        response = self.api.stop_shade(self.device["mac"])
        if response["result"] == "success":
            # Set cover position to some value where up/down are both enabled
            self.current_position = 50
        else:
            super().log_device_unreachable(
                _LOGGER, self.device["name"], response["msg"]
            )

    def set_cover_position(self, **kwargs):
        """Move the cover shutter to a specific position."""
        self.current_position = kwargs[ATTR_POSITION]
        response = self.api.set_shade_position(
            self.device["mac"], 100 - kwargs[ATTR_POSITION]
        )
        if response["result"] != "success":
            super().log_device_unreachable(
                _LOGGER, self.device["name"], response["msg"]
            )

    async def async_update(self):
        """Update the cover with the latest data."""
        try:
            _LOGGER.debug("Soma Shade Update")
            response = await self.hass.async_add_executor_job(
                self.api.get_shade_state, self.device["mac"]
            )
        except RequestException:
            _LOGGER.error("Connection to SOMA Connect failed")
            self.is_available = False
            return
        if response["result"] != "success":
            super().log_device_unreachable(
                _LOGGER, self.device["name"], response["msg"]
            )
            self.is_available = False
            return
        self.current_position = 100 - int(response["position"])
        self.is_available = True
