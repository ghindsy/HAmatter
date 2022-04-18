"""Support for the QNAP QSW sensors."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final

from aioqsw.const import (
    QSD_FAN1_SPEED,
    QSD_FAN2_SPEED,
    QSD_PRODUCT,
    QSD_SYSTEM_BOARD,
    QSD_SYSTEM_SENSOR,
    QSD_SYSTEM_TIME,
    QSD_TEMP,
    QSD_TEMP_MAX,
    QSD_UPTIME,
)

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import TEMP_CELSIUS, TIME_SECONDS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import QswEntity
from .const import ATTR_MAX, DOMAIN, RPM
from .coordinator import QswUpdateCoordinator


@dataclass
class QswSensorEntityDescription(SensorEntityDescription):
    """A class that describes QNAP QSW sensor entities."""

    attributes: dict[str, list[str]] | None = None
    subkey: str | None = None


SENSOR_TYPES: Final[tuple[QswSensorEntityDescription, ...]] = (
    QswSensorEntityDescription(
        key=QSD_SYSTEM_SENSOR,
        name="Fan 1 Speed",
        native_unit_of_measurement=RPM,
        state_class=SensorStateClass.MEASUREMENT,
        subkey=QSD_FAN1_SPEED,
    ),
    QswSensorEntityDescription(
        key=QSD_SYSTEM_SENSOR,
        name="Fan 2 Speed",
        native_unit_of_measurement=RPM,
        state_class=SensorStateClass.MEASUREMENT,
        subkey=QSD_FAN2_SPEED,
    ),
    QswSensorEntityDescription(
        attributes={
            ATTR_MAX: [QSD_SYSTEM_SENSOR, QSD_TEMP_MAX],
        },
        device_class=SensorDeviceClass.TEMPERATURE,
        key=QSD_SYSTEM_SENSOR,
        name="Temperature",
        native_unit_of_measurement=TEMP_CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        subkey=QSD_TEMP,
    ),
    QswSensorEntityDescription(
        key=QSD_SYSTEM_TIME,
        entity_category=EntityCategory.DIAGNOSTIC,
        name="Uptime",
        native_unit_of_measurement=TIME_SECONDS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        subkey=QSD_UPTIME,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add QNAP QSW sensors from a config_entry."""
    coordinator: QswUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        QswSensor(coordinator, description, entry)
        for description in SENSOR_TYPES
        if (
            description.key in coordinator.data
            and description.subkey in coordinator.data[description.key]
        )
    )


class QswSensor(QswEntity, SensorEntity):
    """Define a QNAP QSW sensor."""

    def __init__(
        self,
        coordinator: QswUpdateCoordinator,
        description: QswSensorEntityDescription,
        entry: ConfigEntry,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry)
        self._attr_name = (
            f"{self.get_entity_value(QSD_SYSTEM_BOARD, QSD_PRODUCT)} {description.name}"
        )
        self._attr_unique_id = (
            f"{entry.entry_id}_{description.key}_{description.subkey}"
        )
        self.attributes = description.attributes
        self.entity_description = description

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return state attributes."""
        if not self.attributes:
            return None
        return {
            key: self.get_entity_value(val[0], val[1])
            for key, val in self.attributes.items()
        }

    @property
    def native_value(self):
        """Return the state."""
        return self.get_entity_value(
            self.entity_description.key, self.entity_description.subkey
        )
