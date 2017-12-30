"""
Support for AVM Fritz!Box fritzhome thermostate devices.

For more details about this component, please refer to the documentation at
http://home-assistant.io/components/climate.fritzhome/
"""
import logging

from homeassistant.components.fritzhome import DOMAIN as FRITZHOME_DOMAIN
from homeassistant.components.climate import (
    ATTR_OPERATION_MODE, ClimateDevice, STATE_ECO,
    SUPPORT_OPERATION_MODE, SUPPORT_TARGET_TEMPERATURE)
from homeassistant.const import PRECISION_HALVES
from homeassistant.const import TEMP_CELSIUS, ATTR_TEMPERATURE

DEPENDENCIES = ['fritzhome']

_LOGGER = logging.getLogger(__name__)

STATE_COMFORT = 'comfort'
STATE_MANUAL = 'manual'

SUPPORT_FLAGS = (SUPPORT_TARGET_TEMPERATURE | SUPPORT_OPERATION_MODE)

OPERATION_LIST = [STATE_COMFORT, STATE_ECO, STATE_MANUAL]

MIN_TEMPERATURE = 8
MAX_TEMPERATURE = 28


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Fritzhome thermostat platform."""
    device_list = hass.data[FRITZHOME_DOMAIN]

    devices = []
    for device in device_list:
        if device.has_thermostat:
            devices.append(FritzhomeThermostat(device))

    add_devices(devices)


class FritzhomeThermostat(ClimateDevice):
    """The thermostat class for Fritzhome thermostates."""

    def __init__(self, device):
        """Initialize the thermostat."""
        self._device = device
        self._current_temperature = self._device.actual_temperature
        self._target_temperature = self._device.target_temperature
        self._comfort_temperature = self._device.comfort_temperature
        self._eco_temperature = self._device.eco_temperature

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    @property
    def available(self):
        """Return if thermostat is available."""
        return self._device.present

    @property
    def name(self):
        """Return the name of the device."""
        return self._device.name

    @property
    def temperature_unit(self):
        """Return the unit of measurement that is used."""
        return TEMP_CELSIUS

    @property
    def precision(self):
        """Return precision 0.5."""
        return PRECISION_HALVES

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temperature

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        if ATTR_OPERATION_MODE in kwargs:
            operation_mode = kwargs.get(ATTR_OPERATION_MODE)
            self.set_operation_mode(operation_mode)
        elif ATTR_TEMPERATURE in kwargs:
            temperature = kwargs.get(ATTR_TEMPERATURE)
            self._device.set_target_temperature(temperature)

    @property
    def current_operation(self):
        """Return the current operation mode."""
        if not self.available:
            return None
        if self._target_temperature == self._comfort_temperature:
            return STATE_COMFORT
        elif self._target_temperature == self._eco_temperature:
            return STATE_ECO
        return STATE_MANUAL

    @property
    def operation_list(self):
        """Return the list of available operation modes."""
        return OPERATION_LIST

    def set_operation_mode(self, operation_mode):
        """Set new operation mode."""
        if operation_mode == STATE_COMFORT:
            self.set_temperature(temperature=self._comfort_temperature)
        elif operation_mode == STATE_ECO:
            self.set_temperature(temperature=self._eco_temperature)

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return MIN_TEMPERATURE

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return MAX_TEMPERATURE

    def update(self):
        """Update the data from the thermostat."""
        self._device.update()
        self._current_temperature = self._device.actual_temperature
        self._target_temperature = self._device.target_temperature
        self._comfort_temperature = self._device.comfort_temperature
        self._eco_temperature = self._device.eco_temperature
