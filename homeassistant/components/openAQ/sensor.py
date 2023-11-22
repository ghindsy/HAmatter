"""Sensor platform for OpenAQ."""
from dataclasses import dataclass
from enum import Enum

import homeassistant
from homeassistant.components.sensor import (
    DOMAIN as SENSOR_DOMAIN,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    CONCENTRATION_PARTS_PER_MILLION,
    PERCENTAGE,
    EntityCategory,
    UnitOfPressure,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, ICON


class OpenAQDeviceSensors(str, Enum):
    """Sensors to report in home assistant."""

    Last_Update = SensorDeviceClass.TIMESTAMP
    Air_Quality_index = SensorDeviceClass.AQI
    Particle_Matter_25 = SensorDeviceClass.PM25
    Particle_Matter_10 = SensorDeviceClass.PM10
    Particle_Matter_1 = SensorDeviceClass.PM1
    Concentration_of_Ozone = SensorDeviceClass.OZONE
    Atmospheric_Pressure = SensorDeviceClass.ATMOSPHERIC_PRESSURE
    Temperature = SensorDeviceClass.TEMPERATURE
    Relative_humidity = SensorDeviceClass.HUMIDITY
    Concentration_of_Nitrogen_Dioxide = SensorDeviceClass.NITROGEN_DIOXIDE
    Concentration_of_Nitrogen_Monoxide = SensorDeviceClass.NITROGEN_MONOXIDE
    Concentration_of_Carbon_Monoxide = SensorDeviceClass.CO
    Concentration_of_Carbon_Dioxide = SensorDeviceClass.CO2
    Concentration_of_Sulphure_Dioxide = SensorDeviceClass.SULPHUR_DIOXIDE


@dataclass
class OpenAQSensorDescription(SensorEntityDescription):
    """Class to describe a Sensor entity."""

    metric: Enum | None = None


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_devices: AddEntitiesCallback
) -> None:
    """Configure the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities = []

    for metric in list(OpenAQDeviceSensors):
        if coordinator.data.get(metric.name):
            match metric.value:
                case SensorDeviceClass.TIMESTAMP | SensorDeviceClass.AQI:
                    unit = None
                case SensorDeviceClass.CO | SensorDeviceClass.CO2:
                    unit = CONCENTRATION_PARTS_PER_MILLION
                case SensorDeviceClass.PM25 | SensorDeviceClass.PM10 | SensorDeviceClass.PM1 | SensorDeviceClass.OZONE | SensorDeviceClass.NITROGEN_DIOXIDE | SensorDeviceClass.NITROGEN_MONOXIDE | SensorDeviceClass.SULPHUR_DIOXIDE:
                    unit = CONCENTRATION_MICROGRAMS_PER_CUBIC_METER
                case SensorDeviceClass.ATMOSPHERIC_PRESSURE:
                    unit = UnitOfPressure.BAR
                case SensorDeviceClass.HUMIDITY:
                    unit = PERCENTAGE
                case SensorDeviceClass.TEMPERATURE:
                    unit = UnitOfTemperature.CELSIUS

        entities.append(
            OpenAQSensor(
                hass,
                coordinator.location_id,
                OpenAQSensorDescription(
                    key=metric.name.lower(),
                    name=metric.name.replace("_", " "),
                    metric=metric,
                    entity_category=EntityCategory.DIAGNOSTIC,
                    native_unit_of_measurement=unit,
                ),
            ),
        )
    async_add_devices(entities)


class OpenAQSensor(SensorEntity):
    """OpenAQ sensor"""

    def __init__(
        self,
        hass: HomeAssistant,
        station_id,
        description: OpenAQSensorDescription,
    ) -> None:
        """Init"""
        self.entity_description = description
        self.station_id = station_id
        self.metric = self.entity_description.metric
        self._hass = hass
        self._last_reset = homeassistant.util.dt.utc_from_timestamp(0)
        self._attr_unique_id = ".".join(
            [DOMAIN, self.station_id, self.entity_description.key, SENSOR_DOMAIN]
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.station_id)},
        )
        self._attr_icon = ICON

    @property
    def should_poll(self) -> bool:
        """Return True if entity has to be polled for state.

        False if entity pushes its state to HA.
        """
        return True

    @property
    def state_class(self):
        """Return the state class of the sensor."""
        return None

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return self.metric

    @property
    def native_value(self):
        """Return the state of the sensor, rounding if a number."""
        if self.metric == SensorDeviceClass.TIMESTAMP:
            return None
        return self.coordinator["data"][self.metric]
