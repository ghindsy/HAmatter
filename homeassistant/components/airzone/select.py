"""Support for the Airzone sensors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

from aioairzone.common import GrilleAngle, SleepTimeout
from aioairzone.const import (
    API_COLD_ANGLE,
    API_HEAT_ANGLE,
    API_SLEEP,
    AZD_COLD_ANGLE,
    AZD_HEAT_ANGLE,
    AZD_SLEEP,
    AZD_ZONES,
)

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback

from .entity import AirzoneEntity, AirzoneZoneEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from . import AirzoneConfigEntry
    from .coordinator import AirzoneUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class AirzoneSelectDescription(SelectEntityDescription):
    """Class to describe an Airzone select entity."""

    api_param: str
    options_dict: dict[str, int]


GRILLE_ANGLE_DICT: Final[dict[str, int]] = {
    "90deg": GrilleAngle.DEG_90,
    "50deg": GrilleAngle.DEG_50,
    "45deg": GrilleAngle.DEG_45,
    "40deg": GrilleAngle.DEG_40,
}

SLEEP_DICT: Final[dict[str, int]] = {
    "off": SleepTimeout.SLEEP_OFF,
    "30m": SleepTimeout.SLEEP_30,
    "60m": SleepTimeout.SLEEP_60,
    "90m": SleepTimeout.SLEEP_90,
}


ZONE_SELECT_TYPES: Final[tuple[AirzoneSelectDescription, ...]] = (
    AirzoneSelectDescription(
        api_param=API_COLD_ANGLE,
        entity_category=EntityCategory.CONFIG,
        key=AZD_COLD_ANGLE,
        options=list(GRILLE_ANGLE_DICT),
        options_dict=GRILLE_ANGLE_DICT,
        translation_key="grille_angles",
    ),
    AirzoneSelectDescription(
        api_param=API_HEAT_ANGLE,
        entity_category=EntityCategory.CONFIG,
        key=AZD_HEAT_ANGLE,
        options=list(GRILLE_ANGLE_DICT),
        options_dict=GRILLE_ANGLE_DICT,
        translation_key="heat_angles",
    ),
    AirzoneSelectDescription(
        api_param=API_SLEEP,
        entity_category=EntityCategory.CONFIG,
        key=AZD_SLEEP,
        options=list(SLEEP_DICT),
        options_dict=SLEEP_DICT,
        translation_key="sleep_times",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AirzoneConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add Airzone select from a config_entry."""
    coordinator = entry.runtime_data

    added_zones: set[str] = set()

    def _async_entity_listener() -> None:
        """Handle additions of select."""

        zones_data = coordinator.data.get(AZD_ZONES, {})
        received_zones = set(zones_data)
        new_zones = received_zones - added_zones
        if new_zones:
            async_add_entities(
                AirzoneZoneSelect(
                    coordinator,
                    description,
                    entry,
                    system_zone_id,
                    zones_data.get(system_zone_id),
                )
                for system_zone_id in new_zones
                for description in ZONE_SELECT_TYPES
                if description.key in zones_data.get(system_zone_id)
            )
            added_zones.update(new_zones)

    entry.async_on_unload(coordinator.async_add_listener(_async_entity_listener))
    _async_entity_listener()


class AirzoneBaseSelect(AirzoneEntity, SelectEntity):
    """Define an Airzone select."""

    entity_description: AirzoneSelectDescription
    values_dict: dict[int, str]

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update attributes when the coordinator updates."""
        self._async_update_attrs()
        super()._handle_coordinator_update()

    def _get_current_option(self) -> str | None:
        value = self.get_airzone_value(self.entity_description.key)
        return self.values_dict.get(value)

    @callback
    def _async_update_attrs(self) -> None:
        """Update select attributes."""
        self._attr_current_option = self._get_current_option()


class AirzoneZoneSelect(AirzoneZoneEntity, AirzoneBaseSelect):
    """Define an Airzone Zone select."""

    def __init__(
        self,
        coordinator: AirzoneUpdateCoordinator,
        description: AirzoneSelectDescription,
        entry: ConfigEntry,
        system_zone_id: str,
        zone_data: dict[str, Any],
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, system_zone_id, zone_data)

        self._attr_unique_id = (
            f"{self._attr_unique_id}_{system_zone_id}_{description.key}"
        )
        self.entity_description = description
        self.values_dict = {v: k for k, v in description.options_dict.items()}

        self._async_update_attrs()

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        param = self.entity_description.api_param
        value = self.entity_description.options_dict[option]
        await self._async_update_hvac_params({param: value})
