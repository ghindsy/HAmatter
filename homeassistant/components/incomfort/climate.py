"""Support for an Intergas boiler via an InComfort/InTouch Lan2RF gateway."""

from __future__ import annotations

from typing import Any

from incomfortclient import (
    Gateway as InComfortGateway,
    Heater as InComfortHeater,
    Room as InComfortRoom,
)

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import DOMAIN, IncomfortEntity


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up an InComfort/InTouch climate device."""
    if discovery_info is None:
        return

    client = hass.data[DOMAIN]["client"]
    heaters = hass.data[DOMAIN]["heaters"]

    async_add_entities(
        [InComfortClimate(client, h, r) for h in heaters for r in h.rooms]
    )


class InComfortClimate(IncomfortEntity, ClimateEntity):
    """Representation of an InComfort/InTouch climate device."""

    _attr_min_temp = 5.0
    _attr_max_temp = 30.0
    _attr_hvac_mode = HVACMode.HEAT
    _attr_hvac_modes = [HVACMode.HEAT]
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(
        self, client: InComfortGateway, heater: InComfortHeater, room: InComfortRoom
    ) -> None:
        """Initialize the climate device."""
        super().__init__()

        self._client = client
        self._room = room

        self._attr_unique_id = f"{heater.serial_no}_{room.room_no}"
        self._attr_name = f"Thermostat {room.room_no}"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the device state attributes."""
        return {"status": self._room.status}

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self._room.room_temp

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        return self._room.setpoint

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set a new target temperature for this zone."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        await self._room.set_override(temperature)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
