"""
Support for ComEd Hourly Pricing data.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.comed_hourly_pricing/
"""
from datetime import timedelta
import logging
import voluptuous as vol

from requests import RequestException, get

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)
_RESOURCE = 'https://hourlypricing.comed.com/api'

CONF_ATTRIBUTION = "Data provided by ComEd Hourly Pricing service"

SCAN_INTERVAL = timedelta(minutes=5)

CONF_MONITORED_FEEDS = 'monitored_feeds'
CONF_SENSOR_TYPE = 'type'
CONF_OFFSET = 'offset'
CONF_NAME = 'name'

CONF_FIVE_MINUTE = 'five_minute'
CONF_CURRENT_HOUR_AVERAGE = 'current_hour_average'

SENSOR_TYPES = {
    CONF_FIVE_MINUTE: ['ComEd 5 Minute Price', 'c'],
    CONF_CURRENT_HOUR_AVERAGE: ['ComEd Current Hour Average Price', 'c'],
}

TYPES_SCHEMA = vol.In(SENSOR_TYPES)

SENSORS_SCHEMA = vol.Schema({
    vol.Required(CONF_SENSOR_TYPE): TYPES_SCHEMA,
    vol.Optional(CONF_OFFSET, default=0.0): vol.Coerce(float),
    vol.Optional(CONF_NAME): cv.string
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_MONITORED_FEEDS): [SENSORS_SCHEMA]
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the ComEd Hourly Pricing sensor."""
    dev = []
    for variable in config[CONF_MONITORED_FEEDS]:
        dev.append(ComedHourlyPricingSensor(
            variable[CONF_SENSOR_TYPE], variable[CONF_OFFSET],
            variable.get(CONF_NAME)))

    add_devices(dev)


class ComedHourlyPricingSensor(Entity):
    """Implementation of a ComEd Hourly Pricing sensor."""

    def __init__(self, sensor_type, offset, name):
        """Initialize the sensor."""
        if name:
            self._name = name
        else:
            self._name = SENSOR_TYPES[sensor_type][0]
        self.type = sensor_type
        self.offset = offset
        self._state = None
        self._unit_of_measurement = SENSOR_TYPES[sensor_type][1]

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._unit_of_measurement

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        attrs = {ATTR_ATTRIBUTION: CONF_ATTRIBUTION}
        return attrs

    def update(self):
        """Get the ComEd Hourly Pricing data from the web service."""
        try:
            if self.type == CONF_FIVE_MINUTE:
                url_string = _RESOURCE + '?type=5minutefeed'
                response = get(url_string, timeout=10)
                self._state = float(response.json()[0]['price']) + self.offset
            elif self.type == CONF_CURRENT_HOUR_AVERAGE:
                url_string = _RESOURCE + '?type=currenthouraverage'
                response = get(url_string, timeout=10)
                self._state = float(response.json()[0]['price']) + self.offset
            else:
                self._state = STATE_UNKNOWN
        except (RequestException, ValueError, KeyError):
            _LOGGER.warning('Could not update status for %s', self.name)
