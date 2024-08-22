"""APsystems base entity."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN

if TYPE_CHECKING:
    from . import ApSystemsData


class ApSystemsEntity(Entity):
    """Defines a base APsystems entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        data: ApSystemsData,
    ) -> None:
        """Initialize the APsystems entity."""
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, data.device_id)},
            serial_number=data.device_id,
            manufacturer="APsystems",
            model="EZ1-M",
        )
