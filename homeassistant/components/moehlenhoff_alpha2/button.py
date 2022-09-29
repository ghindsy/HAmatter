"""Support for Alpha2 IO device battery sensors."""

from datetime import datetime

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import Alpha2BaseCoordinator
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add Alpha2 button entities."""

    coordinator: Alpha2BaseCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    async_add_entities([Alpha2TimeSyncButton(coordinator, config_entry.entry_id)])


class Alpha2TimeSyncButton(CoordinatorEntity[Alpha2BaseCoordinator], ButtonEntity):
    """Alpha2 virtual time sync button."""

    _attr_name = "Sync Time"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: Alpha2BaseCoordinator, entry_id: str) -> None:
        """Initialize Alpha2TimeSyncButton."""
        super().__init__(coordinator)

        self._attr_unique_id = f"{entry_id}:sync_time_button"

    async def async_press(self) -> None:
        """Synchronize current local time from HA instance to base station."""
        await self.coordinator.base.set_datetime(datetime.now())
