"""Base Entity for JustNimbus sensors."""
from __future__ import annotations

import justnimbus

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers import update_coordinator
from homeassistant.helpers.entity import DeviceInfo

from . import JustNimbusCoordinator
from .const import DOMAIN


class JustNimbusEntity(
    update_coordinator.CoordinatorEntity[justnimbus.JustNimbusModel],
    SensorEntity,
):
    """Defines a base JustNimbus entity."""

    def __init__(
        self,
        *,
        client: justnimbus.JustNimbusClient,
        entry_id: str,
        device_id: str,
        coordinator: JustNimbusCoordinator,
    ) -> None:
        """Initialize the JustNimbus entity."""
        super().__init__(coordinator=coordinator)
        self._entry_id = entry_id
        self._device_id = device_id
        self.client = client
        if self._device_id:
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, device_id)},
                name="Just Nimbus Sensor",
                manufacturer="Just Nimbus",
                suggested_area="Basement",
                via_device=(DOMAIN, device_id),
            )

    @property
    def available(self) -> bool:
        """Return device availability."""
        return super.available() and getattr(self.coordinator.data, "error_code") == 0
