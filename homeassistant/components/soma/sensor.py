"""Support for Soma sensors."""
from datetime import timedelta

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import Throttle

from . import DEVICES, SomaEntity
from .const import API, DOMAIN

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=30)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Soma sensor platform."""

    devices = hass.data[DOMAIN][DEVICES]

    async_add_entities(
        [SomaSensor(sensor, hass.data[DOMAIN][API]) for sensor in devices], True
    )


class SomaSensor(SomaEntity, SensorEntity):
    """Representation of a Soma cover device."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE

    @property
    def native_value(self):
        """Return the state of the entity."""
        return self.battery_state

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self) -> None:
        """Update the sensor with the latest data."""
        response = await self.get_battery_level_from_api()
        _battery = response["battery_percentage"]
        battery = max(min(100, _battery), 0)
        self.battery_state = battery
