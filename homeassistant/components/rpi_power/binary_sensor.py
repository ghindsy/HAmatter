"""
A sensor platform which detects underruns and capped status from the official Raspberry Pi Kernel.

Minimal Kernel needed is 4.14+
"""
import logging

from rpi_bad_power import UnderVoltage, new_under_voltage

from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_PROBLEM,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)

DESCRIPTION_NORMALIZED = "Voltage normalized. Everything is working as intended."
DESCRIPTION_UNDER_VOLTAGE = "Under-voltage was detected. Consider getting a uninterruptible power supply for your Raspberry Pi."


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up rpi_power binary sensor."""
    under_voltage = await hass.async_add_executor_job(new_under_voltage)
    async_add_entities([RaspberryChargerBinarySensor(under_voltage)], True)


class RaspberryChargerBinarySensor(BinarySensorEntity):
    """Binary sensor representing the rpi power status."""

    def __init__(self, under_voltage: UnderVoltage) -> None:
        """Initialize the binary sensor."""
        self._under_voltage = under_voltage
        self._attr_is_on = None
        self._attr_device_class = DEVICE_CLASS_PROBLEM
        self._attr_icon = "mdi:raspberry-pi"
        self._attr_name = "RPi Power status"
        self._attr_unique_id = "rpi_power"  # only one sensor possible
        self._last_is_on = False

    def update(self) -> None:
        """Update the state."""
        self.attr_is_on = self._under_voltage.get()
        if self.attr_is_on != self._last_is_on:
            if self.attr_is_on:
                _LOGGER.warning(DESCRIPTION_UNDER_VOLTAGE)
            else:
                _LOGGER.info(DESCRIPTION_NORMALIZED)
            self._last_is_on = self.attr_is_on
