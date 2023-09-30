"""DataUpdateCoordinator for the Hydrawise integration."""

from __future__ import annotations

from datetime import timedelta

from aiohttp import ClientError
from pydrawise import HydrawiseBase
from pydrawise.schema import User

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, LOGGER


class HydrawiseDataUpdateCoordinator(DataUpdateCoordinator[User]):
    """The Hydrawise Data Update Coordinator."""

    def __init__(
        self, hass: HomeAssistant, api: HydrawiseBase, scan_interval: timedelta
    ) -> None:
        """Initialize HydrawiseDataUpdateCoordinator."""
        super().__init__(hass, LOGGER, name=DOMAIN, update_interval=scan_interval)
        self.api = api

    async def _async_update_data(self) -> User:
        """Fetch the latest data from Hydrawise."""
        try:
            return await self.api.get_user()
        except ClientError as ex:
            LOGGER.debug("Failed to refresh Hydrawise data: %s", ex)
            raise UpdateFailed("Failed to refresh Hydrawise data") from ex
