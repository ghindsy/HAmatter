"""Select platform for La Marzocco espresso machines."""

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from lmcloud.const import MachineModel, PrebrewMode, SteamLevel
from lmcloud.lm_machine import LaMarzoccoMachine
from lmcloud.models import LaMarzoccoMachineConfig

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import LaMarzoccoEntity, LaMarzoccoEntityDescription

STEAM_LEVEL_HA_TO_LM = {
    "1": SteamLevel.LEVEL_1,
    "2": SteamLevel.LEVEL_2,
    "3": SteamLevel.LEVEL_3,
}

STEAM_LEVEL_LM_TO_HA = {
    SteamLevel.LEVEL_1: "1",
    SteamLevel.LEVEL_2: "2",
    SteamLevel.LEVEL_3: "3",
}

PREBREW_MODE_HA_TO_LM = {
    "disabled": PrebrewMode.DISABLED,
    "prebrew": PrebrewMode.PREBREW,
    "preinfusion": PrebrewMode.PREINFUSION,
}

PREBREW_MODE_LM_TO_HA = {
    PrebrewMode.DISABLED: "disabled",
    PrebrewMode.PREBREW: "prebrew",
    PrebrewMode.PREINFUSION: "preinfusion",
}


@dataclass(frozen=True, kw_only=True)
class LaMarzoccoSelectEntityDescription(
    LaMarzoccoEntityDescription,
    SelectEntityDescription,
):
    """Description of a La Marzocco select entity."""

    current_option_fn: Callable[[LaMarzoccoMachineConfig], str]
    select_option_fn: Callable[[LaMarzoccoMachine, str], Coroutine[Any, Any, bool]]


ENTITIES: tuple[LaMarzoccoSelectEntityDescription, ...] = (
    LaMarzoccoSelectEntityDescription(
        key="steam_temp_select",
        translation_key="steam_temp_select",
        options=["1", "2", "3"],
        select_option_fn=lambda machine, option: machine.set_steam_level(
            STEAM_LEVEL_HA_TO_LM[option]
        ),
        current_option_fn=lambda config: STEAM_LEVEL_LM_TO_HA[config.steam_level],
        supported_fn=lambda coordinator: coordinator.device.model
        == MachineModel.LINEA_MICRA,
    ),
    LaMarzoccoSelectEntityDescription(
        key="prebrew_infusion_select",
        translation_key="prebrew_infusion_select",
        entity_category=EntityCategory.CONFIG,
        options=["disabled", "prebrew", "preinfusion"],
        select_option_fn=lambda machine, option: machine.set_prebrew_mode(
            PREBREW_MODE_HA_TO_LM[option]
        ),
        current_option_fn=lambda config: PREBREW_MODE_LM_TO_HA[config.prebrew_mode],
        supported_fn=lambda coordinator: coordinator.device.model
        in (
            MachineModel.GS3_AV,
            MachineModel.LINEA_MICRA,
            MachineModel.LINEA_MINI,
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up select entities."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    async_add_entities(
        LaMarzoccoSelectEntity(coordinator, description)
        for description in ENTITIES
        if description.supported_fn(coordinator)
    )


class LaMarzoccoSelectEntity(LaMarzoccoEntity, SelectEntity):
    """La Marzocco select entity."""

    entity_description: LaMarzoccoSelectEntityDescription

    @property
    def current_option(self) -> str:
        """Return the current selected option."""
        return str(
            self.entity_description.current_option_fn(self.coordinator.device.config)
        )

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if option != self.current_option:
            await self.entity_description.select_option_fn(
                self.coordinator.device, option
            )
            self.async_write_ha_state()
