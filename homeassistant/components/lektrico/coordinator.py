"""Coordinator for the Lektrico Charging Station integration."""

from __future__ import annotations

from datetime import timedelta

from lektricowifi import DeviceConnectionError, lektricowifi

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import LOGGER

SCAN_INTERVAL = timedelta(seconds=10)


class LektricoDeviceDataUpdateCoordinator(DataUpdateCoordinator):
    """Data update coordinator for Lektrico device."""

    def __init__(
        self,
        hass: HomeAssistant,
        friendly_name: str,
        host: str,
        serial_number: str,
        board_revision: str,
        device_type: str,
    ) -> None:
        """Initialize a Lektrico Device."""
        super().__init__(
            hass,
            LOGGER,
            name=friendly_name,
            update_interval=SCAN_INTERVAL,
        )
        self.device = lektricowifi.Device(
            host,
            session=async_get_clientsession(hass),
        )
        self.serial_number: str = serial_number
        self.board_revision: str = board_revision
        self.device_type: str = device_type

    async def _async_update_data(self) -> lektricowifi.Info:
        """Async Update device state."""
        try:
            return await self.device.device_info(self.device_type)
        except DeviceConnectionError as lek_ex:
            raise UpdateFailed(lek_ex) from lek_ex
