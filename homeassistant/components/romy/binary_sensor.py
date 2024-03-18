"""Checking binary status values from your ROMY."""


from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import RomyVacuumCoordinator
from .entity import RomyEntity

BINARY_SENSORS: list[BinarySensorEntityDescription] = [
    BinarySensorEntityDescription(
        key="dustbin",
        translation_key="dustbin_present",
    ),
    BinarySensorEntityDescription(
        key="dock",
        translation_key="docked",
        device_class=BinarySensorDeviceClass.PLUG,
    ),
    BinarySensorEntityDescription(
        key="water_tank",
        translation_key="water_tank_present",
        device_class=BinarySensorDeviceClass.MOISTURE,
    ),
    BinarySensorEntityDescription(
        key="water_tank_empty",
        translation_key="water_tank_empty",
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ROMY vacuum cleaner."""

    coordinator: RomyVacuumCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    async_add_entities(
        RomyBinarySensor(coordinator, entity_description)
        for entity_description in BINARY_SENSORS
        if entity_description.key in coordinator.romy.binary_sensors
    )


class RomyBinarySensor(
    RomyEntity, CoordinatorEntity[RomyVacuumCoordinator], BinarySensorEntity
):
    """RomyBinarySensor Class."""

    entity_description: BinarySensorEntityDescription

    def __init__(
        self,
        coordinator: RomyVacuumCoordinator,
        entity_description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize ROMYs StatusSensor."""
        RomyEntity.__init__(self, coordinator.romy)
        CoordinatorEntity.__init__(self, coordinator)
        self._attr_unique_id = f"{entity_description.key}_{self.romy.unique_id}"
        self.entity_description = entity_description

    @property
    def is_on(self) -> bool | None:
        """Return the value of the sensor."""
        return self.romy.binary_sensors[self.entity_description.key]
