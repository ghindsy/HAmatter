"""The coordinator for APsystems local API integration."""

from __future__ import annotations

from datetime import timedelta
from typing import TypedDict

from APsystemsEZ1 import APsystemsEZ1M, ReturnAlarmInfo, ReturnOutputData

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import LOGGER


class ApSystemsSensorData(TypedDict):
    """Representing different Apsystems sensor data."""

    output_data: ReturnOutputData
    alarm_info: ReturnAlarmInfo


class ApSystemsDataCoordinator(DataUpdateCoordinator[ApSystemsSensorData]):
    """Coordinator used for all sensors."""

    def __init__(self, hass: HomeAssistant, api: APsystemsEZ1M) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            LOGGER,
            name="APSystems Data",
            update_interval=timedelta(seconds=12),
        )
        self.api = api

    async def _async_update_data(self) -> ApSystemsSensorData:
        output_data = await self.api.get_output_data()
        alarm_info = await self.api.get_alarm_info()
        return ApSystemsSensorData(output_data=output_data, alarm_info=alarm_info)
