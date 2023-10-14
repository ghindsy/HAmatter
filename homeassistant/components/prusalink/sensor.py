"""PrusaLink sensors."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Generic, TypeVar, cast

from pyprusalink import JobInfo, PrinterInfo

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfLength, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.util.dt import utcnow
from homeassistant.util.variance import ignore_variance

from . import DOMAIN, PrusaLinkEntity, PrusaLinkUpdateCoordinator

T = TypeVar("T", PrinterInfo, JobInfo)


@dataclass
class PrusaLinkSensorEntityDescriptionMixin(Generic[T]):
    """Mixin for required keys."""

    value_fn: Callable[[T], datetime | StateType]


@dataclass
class PrusaLinkSensorEntityDescription(
    SensorEntityDescription, PrusaLinkSensorEntityDescriptionMixin[T], Generic[T]
):
    """Describes PrusaLink sensor entity."""

    available_fn: Callable[[T], bool] = lambda _: True


def get_datetime_from_seconds(seconds, multiplier):
    return ignore_variance(
        lambda val: (
                utcnow() + timedelta(seconds=val)
        ),
        timedelta(minutes=2),
    )(seconds * multiplier) if seconds is not None else None


SENSORS: dict[str, tuple[PrusaLinkSensorEntityDescription, ...]] = {
    "printer": (
        PrusaLinkSensorEntityDescription[PrinterInfo](
            key="printer.state",
            name=None,
            icon="mdi:printer-3d",
            value_fn=lambda data: (
                "pausing"
                if (flags := data["state"]["flags"])["pausing"]
                else "cancelling"
                if flags["cancelling"]
                else "paused"
                if flags["paused"]
                else "printing"
                if flags["printing"]
                else "idle"
            ),
            device_class=SensorDeviceClass.ENUM,
            options=["cancelling", "idle", "paused", "pausing", "printing"],
            translation_key="printer_state",
        ),
        PrusaLinkSensorEntityDescription[PrinterInfo](
            key="printer.telemetry.temp-bed",
            translation_key="heatbed_temperature",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda data: cast(float, data["telemetry"]["temp-bed"]),
            entity_registry_enabled_default=False,
        ),
        PrusaLinkSensorEntityDescription[PrinterInfo](
            key="printer.telemetry.temp-nozzle",
            translation_key="nozzle_temperature",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda data: cast(float, data["telemetry"]["temp-nozzle"]),
            entity_registry_enabled_default=False,
        ),
        PrusaLinkSensorEntityDescription[PrinterInfo](
            key="printer.telemetry.temp-bed.target",
            translation_key="heatbed_target_temperature",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda data: cast(float, data["temperature"]["bed"]["target"]),
            entity_registry_enabled_default=False,
        ),
        PrusaLinkSensorEntityDescription[PrinterInfo](
            key="printer.telemetry.temp-nozzle.target",
            translation_key="nozzle_target_temperature",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda data: cast(float, data["temperature"]["tool0"]["target"]),
            entity_registry_enabled_default=False,
        ),
        PrusaLinkSensorEntityDescription[PrinterInfo](
            key="printer.telemetry.z-height",
            translation_key="z_height",
            native_unit_of_measurement=UnitOfLength.MILLIMETERS,
            device_class=SensorDeviceClass.DISTANCE,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda data: cast(float, data["telemetry"]["z-height"]),
            entity_registry_enabled_default=False,
        ),
        PrusaLinkSensorEntityDescription[PrinterInfo](
            key="printer.telemetry.print-speed",
            translation_key="print_speed",
            native_unit_of_measurement=PERCENTAGE,
            value_fn=lambda data: cast(float, data["telemetry"]["print-speed"]),
        ),
        PrusaLinkSensorEntityDescription[PrinterInfo](
            key="printer.telemetry.material",
            translation_key="material",
            icon="mdi:palette-swatch-variant",
            value_fn=lambda data: cast(str, data["telemetry"]["material"]),
        ),
    ),
    "job": (
        PrusaLinkSensorEntityDescription[JobInfo](
            key="job.progress",
            translation_key="progress",
            icon="mdi:progress-clock",
            native_unit_of_measurement=PERCENTAGE,
            value_fn=lambda data: cast(float, data["progress"]["completion"]) * 100 if data["progress"]["completion"] is not None else None,
            available_fn=lambda data: data.get("progress") is not None,
        ),
        PrusaLinkSensorEntityDescription[JobInfo](
            key="job.filename",
            translation_key="filename",
            icon="mdi:file-image-outline",
            value_fn=lambda data: cast(str, data["job"]["file"]["display"]),
            available_fn=lambda data: data.get("job") is not None,
        ),
        PrusaLinkSensorEntityDescription[JobInfo](
            key="job.start",
            translation_key="print_start",
            device_class=SensorDeviceClass.TIMESTAMP,
            icon="mdi:clock-start",
            value_fn=lambda data: get_datetime_from_seconds(data["progress"]["printTime"], -1),
            available_fn=lambda data: data.get("progress") is not None,
        ),
        PrusaLinkSensorEntityDescription[JobInfo](
            key="job.finish",
            translation_key="print_finish",
            icon="mdi:clock-end",
            device_class=SensorDeviceClass.TIMESTAMP,
            value_fn=lambda data: get_datetime_from_seconds(data["progress"]["printTimeLeft"], 1),
            available_fn=lambda data: data.get("progress") is not None,
        ),
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PrusaLink sensor based on a config entry."""
    coordinators: dict[str, PrusaLinkUpdateCoordinator] = hass.data[DOMAIN][
        entry.entry_id
    ]

    entities: list[PrusaLinkEntity] = []

    for coordinator_type, sensors in SENSORS.items():
        coordinator = coordinators[coordinator_type]
        entities.extend(
            PrusaLinkSensorEntity(coordinator, sensor_description)
            for sensor_description in sensors
        )

    async_add_entities(entities)


class PrusaLinkSensorEntity(PrusaLinkEntity, SensorEntity):
    """Defines a PrusaLink sensor."""

    entity_description: PrusaLinkSensorEntityDescription

    def __init__(
        self,
        coordinator: PrusaLinkUpdateCoordinator,
        description: PrusaLinkSensorEntityDescription,
    ) -> None:
        """Initialize a PrusaLink sensor entity."""
        super().__init__(coordinator=coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"

    @property
    def native_value(self) -> datetime | StateType:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def available(self) -> bool:
        """Return if sensor is available."""
        return super().available and self.entity_description.available_fn(
            self.coordinator.data
        )
