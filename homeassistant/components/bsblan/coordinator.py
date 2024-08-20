"""DataUpdateCoordinator for the BSB-Lan integration."""

from datetime import timedelta
from random import randint

from bsblan import BSBLAN, BSBLANConnectionError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, LOGGER, SCAN_INTERVAL
from .models import BSBLanCoordinatorData


class BSBLanUpdateCoordinator(DataUpdateCoordinator[BSBLanCoordinatorData]):
    """The BSB-Lan update coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        client: BSBLAN,
    ) -> None:
        """Initialize the BSB-Lan coordinator."""
        self.client = client
        self.bsblan_config_entry = config_entry

        super().__init__(
            hass,
            logger=LOGGER,
            name=f"{DOMAIN}_{config_entry.data[CONF_HOST]}",
            update_interval=self._get_update_interval(),
        )

    def _get_update_interval(self) -> timedelta:
        """Get the update interval with a random offset.

        Use the default scan interval and add a random number of seconds to avoid timeouts when
        the BSB-Lan device is already/still busy retrieving data,
        e.g. for MQTT or internal logging.
        """
        return SCAN_INTERVAL + timedelta(seconds=randint(1, 8))

    async def _async_update_data(self) -> BSBLanCoordinatorData:
        """Get state and sensor data from BSB-Lan device."""
        try:
            state = await self.client.state()
            sensor = await self.client.sensor()
        except BSBLANConnectionError as err:
            raise UpdateFailed(
                f"Error while establishing connection with "
                f"BSB-Lan device at {self.bsblan_config_entry.data[CONF_HOST]}"
            ) from err

        return BSBLanCoordinatorData(state=state, sensor=sensor)
