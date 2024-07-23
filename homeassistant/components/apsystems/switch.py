"""The power switch which can be toggled via the APsystems local API integration."""

from __future__ import annotations

from typing import Any

from APsystemsEZ1 import Status

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType

from . import ApSystemsConfigEntry, ApSystemsData
from .entity import ApSystemsEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ApSystemsConfigEntry,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the switch platform."""

    add_entities([ApSystemsPowerSwitch(config_entry.runtime_data)])


class ApSystemsPowerSwitch(ApSystemsEntity, SwitchEntity):
    """Base switch to be used with description."""

    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(
        self,
        data: ApSystemsData,
    ) -> None:
        """Initialize the switch."""
        super().__init__(data)
        self._api = data.coordinator.api
        self._attr_unique_id = f"{data.device_id}_power_switch"
        self._state = None

    @property
    def is_on(self) -> bool | None:
        """Return true if device is on."""
        return self._state

    async def async_update(self) -> None:
        try:
            status = await self._api.get_device_power_status()
            self._state = status == Status.normal
            self._attr_available = True
        except Exception:
            self._attr_available = False

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.hass.async_add_executor_job(self._api.set_device_power_status(0))
        await self.async_update()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.hass.async_add_executor_job(self._api.set_device_power_status(1))
        await self.async_update()
