"""The v2c component."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from pytrydan import Trydan, TrydanData
from pytrydan.exceptions import TrydanError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

SCAN_INTERVAL = timedelta(seconds=60)

_LOGGER = logging.getLogger(__name__)


class V2CUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """DataUpdateCoordinator to gather data from any v2c."""

    def __init__(self, hass: HomeAssistant, evse: Trydan, entry: ConfigEntry) -> None:
        """Initialize DataUpdateCoordinator for a v2c evse."""
        self.evse = evse
        entry_data = entry.data
        self.entry = entry
        super().__init__(
            hass,
            _LOGGER,
            name=entry_data[CONF_HOST],
            update_interval=SCAN_INTERVAL,
            always_update=False,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch sensor data from api."""
        try:
            data: TrydanData = await self.evse.get_data()
            return {
                "charge_power": data.charge_power,
            }
        except TrydanError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
