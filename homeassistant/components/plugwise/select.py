"""Plugwise Select component for Home Assistant."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, THERMOSTAT_CLASSES
from .coordinator import PlugwiseDataUpdateCoordinator
from .entity import PlugwiseEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Smile selector from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        PlugwiseSelectEntity(coordinator, device_id)
        for device_id, device in coordinator.data.devices.items()
        if device["class"] in THERMOSTAT_CLASSES
        and len(device.get("available_schedules")) > 1
    )


class PlugwiseSelectEntity(PlugwiseEntity, SelectEntity):
    """Represent Smile selector."""

    def __init__(
        self,
        coordinator: PlugwiseDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialise the selector."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}-select_schedule"
        self._attr_name = (f"{self.device.get('name', '')} Select Schedule").lstrip()
        self._attr_current_option = self.device.get("selected_schedule")
        self._attr_options = self.device.get("available_schedules", [])

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        await self.coordinator.api.set_schedule_state(
            self.device.get("location"),
            option,
            STATE_ON,
        )
