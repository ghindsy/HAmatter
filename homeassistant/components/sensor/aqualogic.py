"""
Support for AquaLogic sensors.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.aqualogic/
"""
import asyncio
import logging

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (CONF_MONITORED_CONDITIONS, 
    TEMP_CELSIUS, TEMP_FAHRENHEIT)
from homeassistant.helpers.entity import Entity
import homeassistant.components.aqualogic as aqualogic
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ['aqualogic']

TEMP_UNITS = [TEMP_CELSIUS, TEMP_FAHRENHEIT]
PERCENT_UNITS = ['%', '%']
SALT_UNITS = ['g/L', 'PPM']
WATT_UNITS = ['W', 'W']
NO_UNITS = [None, None]

# sensor_type [ description, unit, icon ]
# sensor_type corresponds to property names in aqualogic.core.AquaLogic
SENSOR_TYPES = {
    'air_temp': ['Air Temperature', TEMP_UNITS, 'mdi:thermometer'],
    'pool_temp': ['Pool Temperature', TEMP_UNITS, 'mdi:oil-temperature'],
    'spa_temp': ['Spa Temperature', TEMP_UNITS, 'mdi:oil-temperature'],
    'pool_chlorinator': ['Pool Chlorinator', PERCENT_UNITS, 'mdi:gauge'],
    'spa_chlorinator': ['Spa Chlorinator', PERCENT_UNITS, 'mdi:gauge'],
    'salt_level': ['Salt Level', SALT_UNITS, 'mdi:gauge'],
    'pump_speed': ['Pump Speed', PERCENT_UNITS, 'mdi:speedometer'],
    'pump_power': ['Pump Power', WATT_UNITS, 'mdi:gauge'],
    'status': ['Status', NO_UNITS, 'mdi:alert']
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_MONITORED_CONDITIONS, default=list(SENSOR_TYPES)):
        vol.All(cv.ensure_list, [vol.In(SENSOR_TYPES)]),
})

@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up the sensor platform."""
    sensors = []

    component = hass.data[aqualogic.DOMAIN]
    for sensor_type in config.get(CONF_MONITORED_CONDITIONS):
        sensors.append(AquaLogicSensor(component, sensor_type))

    async_add_devices(sensors)


class AquaLogicSensor(Entity):
    """Sensor implementation for the AquaLogic component."""

    def __init__(self, component, sensor_type):
        """Initialize sensor."""
        self._component = component
        self._type = sensor_type
        self._state = None

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def name(self):
        return "AquaLogic {}".format(SENSOR_TYPES[self._type][0])

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement the value is expressed in."""
        panel = self._component.panel;
        if panel == None:
            return None
        if panel.is_metric:
            return SENSOR_TYPES[self._type][1][0]
        else:
            return SENSOR_TYPES[self._type][1][1]

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return SENSOR_TYPES[self._type][2]

    def update(self):
        """Update the sensor."""
        panel = self._component.panel;
        if panel == None:
            return
        self._state = getattr(panel, self._type)
