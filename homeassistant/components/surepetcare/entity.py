"""Entity for Surepetcare."""
from __future__ import annotations

from abc import abstractmethod

from surepy.entities import SurepyEntity

from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SurePetcareDataCoordinator


class SurePetcareEntity(CoordinatorEntity):
    """An implementation for Sure Petcare Entities."""

    def __init__(
        self,
        _id: int,
        coordinator: SurePetcareDataCoordinator,
    ) -> None:
        """Initialize a Sure Petcare entity."""
        super().__init__(coordinator)

        self._id = _id

        surepy_entity: SurepyEntity = coordinator.data[_id]

        self._device_name = surepy_entity.type.name.capitalize().replace("_", " ")
        if surepy_entity.name:
            self._device_name = f"{self._device_name} {surepy_entity.name.capitalize()}"

        self._device_id = f"{surepy_entity.household_id}-{_id}"
        self._update_attr(coordinator.data[_id])

    @abstractmethod
    @callback
    def _update_attr(self, surepy_entity: SurepyEntity) -> None:
        """Update the state and attributes."""

    @callback
    def _handle_coordinator_update(self) -> None:
        """Get the latest data and update the state."""
        self._update_attr(self.coordinator.data[self._id])
        self.async_write_ha_state()
