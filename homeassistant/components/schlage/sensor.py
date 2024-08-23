"""Platform for Schlage sensor integration."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SchlageDataUpdateCoordinator
from .entity import SchlageEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors based on a config entry."""
    coordinator: SchlageDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        pyclass(
            coordinator=coordinator,
            description=description,
            device_id=device_id,
        )
        for (pyclass, description) in _SENSOR_DESCRIPTIONS
        for device_id in coordinator.data.locks
    )


class SchlageSensor(SchlageEntity, SensorEntity):
    """Schlage base sensor entity."""

    def __init__(
        self,
        coordinator: SchlageDataUpdateCoordinator,
        description: SensorEntityDescription,
        device_id: str,
    ) -> None:
        """Initialize a Schlage battery sensor."""
        super().__init__(coordinator=coordinator, device_id=device_id)
        self.entity_description = description
        self._attr_unique_id = f"{device_id}_{description.key}"
        self._attr_native_value = getattr(self._lock, self.entity_description.key)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = getattr(self._lock, self.entity_description.key)
        return super()._handle_coordinator_update()


class SchlageBatterySensor(SchlageSensor):
    """Schlage battery sensor entity."""


class SchlageDurationSensor(SchlageSensor):
    """Schlage duration sensor entity."""


_SENSOR_DESCRIPTIONS: list[tuple[type[SchlageSensor], SensorEntityDescription]] = [
    (
        SchlageBatterySensor,
        SensorEntityDescription(
            key="battery_level",
            device_class=SensorDeviceClass.BATTERY,
            entity_category=EntityCategory.DIAGNOSTIC,
            native_unit_of_measurement=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
    ),
    (
        SchlageDurationSensor,
        SensorEntityDescription(
            key="auto_lock_time",
            device_class=SensorDeviceClass.DURATION,
            entity_category=EntityCategory.DIAGNOSTIC,
            native_unit_of_measurement=UnitOfTime.SECONDS,
            state_class=SensorStateClass.MEASUREMENT,
        ),
    ),
]
