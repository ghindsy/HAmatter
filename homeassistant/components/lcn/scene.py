"""Support for LCN scenes."""

from __future__ import annotations

from typing import Any

import pypck

from homeassistant.components.scene import DOMAIN as DOMAIN_SCENE, Scene
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DOMAIN, CONF_ENTITIES, CONF_SCENE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType

from . import LcnEntity
from .const import (
    ADD_ENTITIES_CALLBACKS,
    CONF_DOMAIN_DATA,
    CONF_OUTPUTS,
    CONF_REGISTER,
    CONF_TRANSITION,
    DOMAIN,
    OUTPUT_PORTS,
)

PARALLEL_UPDATES = 0


def create_lcn_scene_entity(
    entity_config: ConfigType, config_entry: ConfigEntry
) -> LcnEntity:
    """Set up an entity for this domain."""
    return LcnScene(entity_config, config_entry)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up LCN switch entities from a config entry."""
    hass.data[DOMAIN][config_entry.entry_id][ADD_ENTITIES_CALLBACKS].update(
        {DOMAIN_SCENE: (async_add_entities, create_lcn_scene_entity)}
    )

    async_add_entities(
        create_lcn_scene_entity(entity_config, config_entry)
        for entity_config in config_entry.data[CONF_ENTITIES]
        if entity_config[CONF_DOMAIN] == DOMAIN_SCENE
    )


class LcnScene(LcnEntity, Scene):
    """Representation of a LCN scene."""

    def __init__(self, config: ConfigType, config_entry: ConfigEntry) -> None:
        """Initialize the LCN scene."""
        super().__init__(config, config_entry)

        self.register_id = config[CONF_DOMAIN_DATA][CONF_REGISTER]
        self.scene_id = config[CONF_DOMAIN_DATA][CONF_SCENE]
        self.output_ports = []
        self.relay_ports = []

        for port in config[CONF_DOMAIN_DATA][CONF_OUTPUTS]:
            if port in OUTPUT_PORTS:
                self.output_ports.append(pypck.lcn_defs.OutputPort[port])
            else:  # in RELEAY_PORTS
                self.relay_ports.append(pypck.lcn_defs.RelayPort[port])

        if config[CONF_DOMAIN_DATA][CONF_TRANSITION] is None:
            self.transition = None
        else:
            self.transition = pypck.lcn_defs.time_to_ramp_value(
                config[CONF_DOMAIN_DATA][CONF_TRANSITION]
            )

    async def async_activate(self, **kwargs: Any) -> None:
        """Activate scene."""
        await self.device_connection.activate_scene(
            self.register_id,
            self.scene_id,
            self.output_ports,
            self.relay_ports,
            self.transition,
        )
