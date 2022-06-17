"""Support for Fibaro sensors."""
from __future__ import annotations

from contextlib import suppress
from typing import Any

from homeassistant.components.sensor import (
    ENTITY_ID_FORMAT,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    ENERGY_KILO_WATT_HOUR,
    LIGHT_LUX,
    PERCENTAGE,
    POWER_WATT,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import convert

from . import FIBARO_DEVICES, FibaroDevice
from .const import DOMAIN

# List of known sensors which represents a fibaro device
MAIN_SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="com.fibaro.temperatureSensor",
        name="Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="com.fibaro.smokeSensor",
        name="Smoke",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        icon="mdi:fire",
    ),
    SensorEntityDescription(
        key="CO2",
        name="CO2",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        device_class=SensorDeviceClass.CO2,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="com.fibaro.humiditySensor",
        name="Humidity",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="com.fibaro.lightSensor",
        name="Light",
        native_unit_of_measurement=LIGHT_LUX,
        device_class=SensorDeviceClass.ILLUMINANCE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="com.fibaro.energyMeter",
        name="Energy",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
)

# List of additional sensors which are created based on a property
# The key is the property name
ADDITIONAL_SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="energy",
        name="Energy",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key="power",
        name="Power",
        native_unit_of_measurement=POWER_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
)

FIBARO_TO_HASS_UNIT: dict[str, str] = {
    "lux": LIGHT_LUX,
    "C": TEMP_CELSIUS,
    "F": TEMP_FAHRENHEIT,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Fibaro controller devices."""
    entities: list[SensorEntity] = []

    for device in hass.data[DOMAIN][entry.entry_id][FIBARO_DEVICES][Platform.SENSOR]:
        entity_description = None
        for desc in MAIN_SENSOR_TYPES:
            if desc.key == device.type:
                entity_description = desc
                break
        # main sensors are created even if the entity type is not known
        entities.append(FibaroSensor(device, entity_description))

    for platform in (Platform.COVER, Platform.LIGHT, Platform.SENSOR, Platform.SWITCH):
        for device in hass.data[DOMAIN][entry.entry_id][FIBARO_DEVICES][platform]:
            for entity_description in ADDITIONAL_SENSOR_TYPES:
                if entity_description.key in device.properties:
                    entities.append(FibaroAdditionalSensor(device, entity_description))

    async_add_entities(entities, True)


class FibaroSensor(FibaroDevice, SensorEntity):
    """Representation of a Fibaro Sensor."""

    def __init__(
        self, fibaro_device: Any, entity_description: SensorEntityDescription | None
    ) -> None:
        """Initialize the sensor."""
        super().__init__(fibaro_device)
        if entity_description is not None:
            self.entity_description = entity_description
        self.entity_id = ENTITY_ID_FORMAT.format(self.ha_id)

        # Map unit if it was not defined in the entity description
        # or there is no entity description at all
        with suppress(KeyError, ValueError):
            if not self.native_unit_of_measurement:
                self._attr_native_unit_of_measurement = FIBARO_TO_HASS_UNIT.get(
                    fibaro_device.properties.unit, fibaro_device.properties.unit
                )

    def update(self):
        """Update the state."""
        with suppress(KeyError, ValueError):
            self._attr_native_value = float(self.fibaro_device.properties.value)


class FibaroAdditionalSensor(FibaroDevice, SensorEntity):
    """Representation of a Fibaro Additional Sensor."""

    def __init__(
        self, fibaro_device: Any, entity_description: SensorEntityDescription
    ) -> None:
        """Initialize the sensor."""
        super().__init__(fibaro_device)
        self.entity_description = entity_description

        # To differentiate additional sensors from main sensors they need
        # to get different names and ids
        self.entity_id = ENTITY_ID_FORMAT.format(
            f"{self.ha_id}_{entity_description.key}"
        )
        self._attr_name = f"{fibaro_device.friendly_name} {entity_description.name}"
        self._attr_unique_id = f"{fibaro_device.unique_id_str}_{entity_description.key}"

    def update(self) -> None:
        """Update the state."""
        with suppress(KeyError, ValueError):
            self._attr_native_value = convert(
                self.fibaro_device.properties[self.entity_description.key],
                float,
            )
