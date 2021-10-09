"""Support for the Environment Canada radar imagery."""
from __future__ import annotations

import datetime
from functools import partial
import logging

from env_canada import ECData, get_station_coords
import voluptuous as vol

from homeassistant.components.camera import PLATFORM_SCHEMA, Camera
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME,
)
import homeassistant.helpers.config_validation as cv
from homeassistant.util import Throttle

from . import trigger_import
from .const import CONF_ATTRIBUTION, CONF_LANGUAGE, CONF_STATION, DOMAIN

CONF_LOOP = "loop"
CONF_PRECIP_TYPE = "precip_type"
ATTR_UPDATED = "updated"

MIN_TIME_BETWEEN_UPDATES = datetime.timedelta(minutes=10)

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_LOOP, default=True): cv.boolean,
        vol.Optional(CONF_NAME): cv.string,
        vol.Optional(CONF_STATION): cv.matches_regex(r"^C[A-Z]{4}$|^[A-Z]{3}$"),
        vol.Inclusive(CONF_LATITUDE, "latlon"): cv.latitude,
        vol.Inclusive(CONF_LONGITUDE, "latlon"): cv.longitude,
        vol.Optional(CONF_PRECIP_TYPE): vol.In(["RAIN", "SNOW"]),
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Environment Canada camera."""
    _LOGGER.warning(
        "Environment Canada YAML configuration is deprecated; your YAML configuration "
        "has been imported into the UI and can be safely removed"
    )
    if config.get(CONF_STATION):
        lat, lon = await hass.async_add_executor_job(
            get_station_coords, config[CONF_STATION]
        )
    else:
        lat = config.get(CONF_LATITUDE, hass.config.latitude)
        lon = config.get(CONF_LONGITUDE, hass.config.longitude)

    weather_init = partial(ECData, coordinates=(lat, lon))
    ec_data = await hass.async_add_executor_job(weather_init)

    config[CONF_STATION] = ec_data.station_id
    config[CONF_LATITUDE] = lat
    config[CONF_LONGITUDE] = lon

    trigger_import(hass, ec_data, config)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add a weather entity from a config_entry."""
    radar_data = hass.data[DOMAIN][config_entry.entry_id]["radar_data"]
    config = config_entry.data

    # The combination of station and language are unique for all EC weather reporting
    unique_id = f"{config[CONF_STATION]}-{config[CONF_LANGUAGE]}-radar"

    async_add_entities(
        [
            ECCamera(radar_data, config.get(CONF_NAME, ""), False, unique_id),
        ]
    )


class ECCamera(Camera):
    """Implementation of an Environment Canada radar camera."""

    def __init__(self, radar_object, camera_name, is_loop, unique_id):
        """Initialize the camera."""
        super().__init__()

        self.radar_object = radar_object
        self.camera_name = camera_name
        self.is_loop = is_loop
        self.uniqueid = unique_id
        self.content_type = "image/gif"
        self.image = None
        self.timestamp = None

    @property
    def unique_id(self):
        """Return unique ID."""
        return self.uniqueid

    def camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return bytes of camera image."""
        self.update()
        return self.image

    @property
    def name(self):
        """Return the name of the camera."""
        if self.camera_name is not None:
            return self.camera_name
        return "Environment Canada Radar"

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the device."""
        return {ATTR_ATTRIBUTION: CONF_ATTRIBUTION, ATTR_UPDATED: self.timestamp}

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Update radar image."""
        if self.is_loop:
            self.image = self.radar_object.get_loop()
        else:
            self.image = self.radar_object.get_latest_frame()
        self.timestamp = self.radar_object.timestamp
