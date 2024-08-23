"""DataUpdateCoordinator for the Squeezebox integration."""

from asyncio import timeout
from datetime import timedelta
import logging

from pysqueezebox import Server

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    SENSOR_UPDATE_INTERVAL,
    STATUS_API_TIMEOUT,
    STATUS_SENSOR_NEEDSRESTART,
    STATUS_SENSOR_RESCAN,
)

_LOGGER = logging.getLogger(__name__)


class LMSStatusDataUpdateCoordinator(DataUpdateCoordinator):
    """LMS Status custom coordinator."""

    def __init__(self, hass: HomeAssistant, lms: Server) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=lms.name,
            update_interval=timedelta(seconds=SENSOR_UPDATE_INTERVAL),
            always_update=False,
        )
        self.lms = lms

    async def _async_update_data(self):
        """Fetch data fromn LMS status call.

        Then we process only a subset to make then nice for HA
        """
        async with timeout(STATUS_API_TIMEOUT):
            data = await self.lms.async_status()

        if not data:
            raise UpdateFailed("No data from status poll")
        _LOGGER.debug("Raw serverstatus %s=%s", self.lms.name, data)

        return self._prepare_status_data(data)

    def _prepare_status_data(self, data: dict) -> dict:
        """Sensors that need the data changing for HA presentation."""

        # rescan bool are we rescanning alter poll not always present
        data[STATUS_SENSOR_RESCAN] = STATUS_SENSOR_RESCAN in data and True or False
        # needsrestart bool plugin updates... not always present
        data[STATUS_SENSOR_NEEDSRESTART] = (
            STATUS_SENSOR_NEEDSRESTART in data and True or False
        )
        _LOGGER.debug("Processed serverstatus %s=%s", self.lms.name, data)
        return data
