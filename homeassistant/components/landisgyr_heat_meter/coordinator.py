"""Data update coordinator for the ultraheat api."""

import logging

import async_timeout
import serial

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import POLLING_INTERVAL, ULTRAHEAT_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class UltraheatCoordinator(DataUpdateCoordinator):
    """Coordinator for getting data from the ultraheat api."""

    def __init__(self, hass, api):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="ultraheat",
            update_interval=POLLING_INTERVAL,
        )
        self.api = api

    async def _async_update_data(self):
        """Fetch data from API endpoint."""
        try:
            async with async_timeout.timeout(ULTRAHEAT_TIMEOUT):
                return await self.hass.async_add_executor_job(self.api.read)
        except (FileNotFoundError, serial.serialutil.SerialException) as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
