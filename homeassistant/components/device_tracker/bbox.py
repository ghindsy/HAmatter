"""
Support for French FAI Bouygues Bbox routers.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/device_tracker.bbox/
"""

from collections import namedtuple
import logging
from datetime import timedelta

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.device_tracker import (
    PLATFORM_SCHEMA, DOMAIN, DeviceScanner)
from homeassistant.const import CONF_HOST

import homeassistant.util.dt as dt_util
from homeassistant.util import Throttle

REQUIREMENTS = ['pybbox==0.0.5-alpha']

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = vol.All(
    PLATFORM_SCHEMA.extend({
        vol.Optional(CONF_HOST, default='192.168.1.254'): cv.string
    }))

MIN_TIME_BETWEEN_SCANS = timedelta(seconds=60)


def get_scanner(hass, config):
    """Validate the configuration and return a Bbox scanner."""
    scanner = BboxDeviceScanner(config[DOMAIN])

    return scanner if scanner.success_init else None


Device = namedtuple('Device', ['mac', 'name', 'ip', 'last_update'])


class BboxDeviceScanner(DeviceScanner):
    """This class scans for devices connected to the bbox."""

    def __init__(self, config):
        """Get host from config."""
        self.host = config[CONF_HOST]

        """Initialize the scanner."""
        self.last_results = []  # type: List[Device]

        self.success_init = self._update_info()
        _LOGGER.info("Scanner initialized")

    def scan_devices(self):
        """Scan for new devices and return a list with found device IDs."""
        self._update_info()

        return [device.mac for device in self.last_results]

    def get_device_name(self, device):
        """Return the name of the given device or None if we don't know."""
        filter_named = [result.name for result in self.last_results if
                        result.mac == device]

        if filter_named:
            return filter_named[0]
        return None

    @Throttle(MIN_TIME_BETWEEN_SCANS)
    def _update_info(self):
        """Check the Bbox for devices.

        Returns boolean if scanning successful.
        """
        _LOGGER.info("Scanning...")

        import pybbox

        box = pybbox.Bbox(ip=self.host)
        result = box.get_all_connected_devices()

        now = dt_util.now()
        last_results = []
        for device in result:
            if device['active'] != 1:
                continue
            last_results.append(
                Device(device['macaddress'], device['hostname'],
                       device['ipaddress'], now))

        self.last_results = last_results

        _LOGGER.info("Scan successful")
        return True
