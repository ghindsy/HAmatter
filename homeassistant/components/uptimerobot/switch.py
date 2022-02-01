"""UptimeRobot switch platform."""
from __future__ import annotations

from typing import Any

from pyuptimerobot import UptimeRobotAuthenticationException

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import UptimeRobotDataUpdateCoordinator
from .const import API_ATTR_OK, DOMAIN, LOGGER
from .entity import UptimeRobotEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the UptimeRobot switches."""
    coordinator: UptimeRobotDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            UptimeRobotSwitch(
                coordinator,
                SwitchEntityDescription(
                    key=str(monitor.id),
                    name=f"{monitor.friendly_name} Pause",
                    device_class=SwitchDeviceClass.SWITCH,
                ),
                monitor=monitor,
            )
            for monitor in coordinator.data
        ],
    )


class UptimeRobotSwitch(UptimeRobotEntity, SwitchEntity):
    """Representation of a UptimeRobot switch."""

    _attr_icon = "mdi:cog"

    @property
    def is_on(self) -> bool:
        """Return True if the entity is on."""
        return bool(self.monitor.status == 0)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.monitor.status not in (8, 9)

    async def _async_edit_monitor(self, **kwargs: Any) -> None:
        """Edit monitor status."""
        try:
            response = await self.api.async_edit_monitor(**kwargs)
            self.async_write_ha_state()
        except UptimeRobotAuthenticationException:
            LOGGER.error(
                "Authentication Error: Please check the provided credentials and verify that you can log into the web interface",
                exc_info=True,
            )
        else:
            if response.status != API_ATTR_OK:
                LOGGER.error(
                    "Switch API exception: %s", response.error.message, exc_info=True
                )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn on switch."""
        await self._async_edit_monitor(id=self.monitor.id, status=1)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn off switch."""
        await self._async_edit_monitor(id=self.monitor.id, status=0)
