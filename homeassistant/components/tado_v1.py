"""
Support for the (unofficial) tado api.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/tado_v1/
"""

import logging
import urllib

import voluptuous as vol
from datetime import timedelta

from homeassistant.helpers.discovery import load_platform
from homeassistant.helpers import config_validation as cv
from homeassistant.const import (
    CONF_USERNAME, CONF_PASSWORD)
from homeassistant.util import Throttle


_LOGGER = logging.getLogger(__name__)

DOMAIN = 'tado_v1'

REQUIREMENTS = ['https://github.com/wmalgadey/PyTado/archive/'
                '0.1.10.zip#'
                'PyTado==0.1.10']

TADO_V1_COMPONENTS = [
    'sensor', 'climate'
]

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_USERNAME, default=''): cv.string,
        vol.Required(CONF_PASSWORD, default=''): cv.string
    })
}, extra=vol.ALLOW_EXTRA)

MIN_TIME_BETWEEN_SCANS = timedelta(seconds=10)


def setup(hass, config):
    """Your controller/hub specific code."""
    username = config[DOMAIN][CONF_USERNAME]
    password = config[DOMAIN][CONF_PASSWORD]

    from PyTado.interface import Tado

    try:
        tado = Tado(username, password)
    except (RuntimeError, urllib.error.HTTPError):
        _LOGGER.error("Unable to connect to mytado with username and password")
        return False

    hass.data['tado_v1_data'] = TadoDataStore(tado, MIN_TIME_BETWEEN_SCANS)

    for component in TADO_V1_COMPONENTS:
        load_platform(hass, component, DOMAIN, {}, config)

    return True


class TadoDataStore:
    """An object to store the tado data."""

    def __init__(self, tado, interval):
        """Initialize Tado data store."""
        self.tado = tado

        self.sensors = {}
        self.data = {}

        # Apply throttling to methods using configured interval
        self.update = Throttle(interval)(self._update)

    def _update(self):
        """Update the internal data from mytado.com."""
        for data_id, sensor in self.sensors.items():
            data = None

            try:
                if "zone" in sensor:
                    _LOGGER.info("querying mytado.com for zone %s %s",
                                 sensor["id"], sensor["name"])
                    data = self.tado.getState(sensor["id"])

                if "device" in sensor:
                    _LOGGER.info("querying mytado.com for device %s %s",
                                 sensor["id"], sensor["name"])
                    data = self.tado.getDevices()[0]

            except RuntimeError:
                _LOGGER.error("Unable to connect to myTado. %s %s",
                              sensor["id"], sensor["id"])

            self.data[data_id] = data

    def add_sensor(self, data_id, sensor):
        """Add a sensor to update in _update()."""
        self.sensors[data_id] = sensor
        self.data[data_id] = None

    def get_data(self, data_id):
        """Get the cached data."""
        data = {"error": "no data"}

        if data_id in self.data:
            data = self.data[data_id]

        return data

    def get_zones(self):
        """Wrapper for getZones()."""
        return self.tado.getZones()

    def get_capabilities(self, tado_id):
        """Wrapper for getCapabilities(..)."""
        return self.tado.getCapabilities(tado_id)

    def get_me(self):
        """Wrapper for getMet()."""
        return self.tado.getMe()

    def reset_zone_overlay(self, zone_id):
        """Wrapper for resetZoneOverlay(..)."""
        return self.tado.resetZoneOverlay(zone_id)

    def set_zone_overlay(self, zone_id, mode, temperature):
        """Wrapper for setZoneOverlay(..)."""
        return self.tado.setZoneOverlay(zone_id, mode, temperature)
