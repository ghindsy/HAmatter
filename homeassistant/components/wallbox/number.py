"""Home Assistant component for accessing the Wallbox Portal API.

The number component allows control of charging current.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    BIDIRECTIONAL_MODEL_PREFIXES,
    CHARGER_DATA_KEY,
    CHARGER_ENERGY_PRICE_KEY,
    CHARGER_MAX_AVAILABLE_POWER_KEY,
    CHARGER_MAX_CHARGING_CURRENT_KEY,
    CHARGER_PART_NUMBER_KEY,
    CHARGER_SERIAL_NUMBER_KEY,
    DOMAIN,
)
from .coordinator import InvalidAuth, WallboxCoordinator
from .entity import WallboxEntity


@dataclass
class WallboxNumberEntityDescription(NumberEntityDescription):
    """Describes Wallbox number entity."""


NUMBER_TYPES: dict[str, WallboxNumberEntityDescription] = {
    CHARGER_MAX_CHARGING_CURRENT_KEY: WallboxNumberEntityDescription(
        key=CHARGER_MAX_CHARGING_CURRENT_KEY,
        translation_key="maximum_charging_current",
        native_min_value=0,
        native_max_value=6,
        native_step=1,
    ),
    CHARGER_ENERGY_PRICE_KEY: WallboxNumberEntityDescription(
        key=CHARGER_ENERGY_PRICE_KEY,
        translation_key="energy_price",
        native_min_value=-5,
        native_max_value=5,
        native_step=0.1,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Create wallbox number entities in HASS."""
    coordinator: WallboxCoordinator = hass.data[DOMAIN][entry.entry_id]
    # Check if the user has sufficient rights to change values, if so, add number component:
    try:
        await coordinator.async_set_charging_current(
            coordinator.data[CHARGER_MAX_CHARGING_CURRENT_KEY]
        )
    except InvalidAuth:
        return
    except ConnectionError as exc:
        raise PlatformNotReady from exc

    async_add_entities(
        [
            WallboxNumber(coordinator, entry, description)
            for ent in coordinator.data
            if (description := NUMBER_TYPES.get(ent))
        ]
    )


class WallboxNumber(WallboxEntity, NumberEntity):
    """Representation of the Wallbox portal."""

    entity_description: WallboxNumberEntityDescription

    def __init__(
        self,
        coordinator: WallboxCoordinator,
        entry: ConfigEntry,
        description: WallboxNumberEntityDescription,
    ) -> None:
        """Initialize a Wallbox number entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._coordinator = coordinator
        self._attr_unique_id = f"{description.key}-{coordinator.data[CHARGER_DATA_KEY][CHARGER_SERIAL_NUMBER_KEY]}"
        self._is_bidirectional = (
            coordinator.data[CHARGER_DATA_KEY][CHARGER_PART_NUMBER_KEY][0:2]
            in BIDIRECTIONAL_MODEL_PREFIXES
        )

    @property
    def native_max_value(self) -> float:
        """Return the maximum available current."""
        return cast(
            float,
            (
                self._coordinator.data[CHARGER_MAX_AVAILABLE_POWER_KEY]
                if self.entity_description.key == CHARGER_MAX_CHARGING_CURRENT_KEY
                else self.entity_description.native_max_value
            ),
        )

    @property
    def native_min_value(self) -> float:
        """Return the minimum available current based on charger type - some chargers can discharge."""
        return cast(
            float,
            (
                (self.max_value * -1)
                if self._is_bidirectional
                and self.entity_description.key == CHARGER_MAX_CHARGING_CURRENT_KEY
                else self.entity_description.native_min_value
            ),
        )

    @property
    def native_value(self) -> float | None:
        """Return the value of the entity."""
        return cast(float | None, self._coordinator.data[self.entity_description.key])

    async def async_set_native_value(self, value: float) -> None:
        """Set the value of the entity."""
        if self.entity_description.key == CHARGER_MAX_CHARGING_CURRENT_KEY:
            await self._coordinator.async_set_charging_current(value)
        if self.entity_description.key == CHARGER_ENERGY_PRICE_KEY:
            await self._coordinator.async_set_energy_cost(value)
