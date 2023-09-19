"""Event for Shelly."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

from aioshelly.block_device import Block

from homeassistant.components.event import (
    DOMAIN as EVENT_DOMAIN,
    EventDeviceClass,
    EventEntity,
    EventEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BLOCK_INPUTS_EVENTS_TYPES, RPC_INPUTS_EVENTS_TYPES
from .coordinator import ShellyBlockCoordinator, ShellyRpcCoordinator, get_entry_data
from .utils import (
    async_remove_shelly_entity,
    get_device_entry_gen,
    get_rpc_input_name,
    get_rpc_key_instances,
    is_block_momentary_input,
    is_rpc_momentary_input,
)


@dataclass
class ShellyRpcEventDescription(EventEntityDescription):
    """Class to describe Shelly event."""

    removal_condition: Callable[[dict, dict, str], bool] | None = None


@dataclass
class ShellyBlockEventDescription(EventEntityDescription):
    """Class to describe Shelly event."""

    removal_condition: Callable[[dict, Block], bool] | None = None


RPC_EVENT: Final = ShellyRpcEventDescription(
    key="input",
    translation_key="input",
    device_class=EventDeviceClass.BUTTON,
    event_types=list(RPC_INPUTS_EVENTS_TYPES),
    removal_condition=lambda config, status, key: not is_rpc_momentary_input(
        config, status, key
    ),
)
BLOCK_EVENT: Final = ShellyBlockEventDescription(
    key="input",
    device_class=EventDeviceClass.BUTTON,
    event_types=list(BLOCK_INPUTS_EVENTS_TYPES),
    removal_condition=lambda settings, block: not is_block_momentary_input(
        settings, block, True
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors for device."""
    entities: list[ShellyBlockEvent | ShellyRpcEvent] = []

    coordinator: ShellyRpcCoordinator | ShellyBlockCoordinator | None = None

    if get_device_entry_gen(config_entry) == 2:
        coordinator = get_entry_data(hass)[config_entry.entry_id].rpc
        if TYPE_CHECKING:
            assert coordinator

        key_instances = get_rpc_key_instances(coordinator.device.status, RPC_EVENT.key)

        for key in key_instances:
            if RPC_EVENT.removal_condition and RPC_EVENT.removal_condition(
                coordinator.device.config, coordinator.device.status, key
            ):
                unique_id = f"{coordinator.mac}-{key}"
                async_remove_shelly_entity(hass, EVENT_DOMAIN, unique_id)
            else:
                entities.append(ShellyRpcEvent(coordinator, key, RPC_EVENT))
    else:
        coordinator = get_entry_data(hass)[config_entry.entry_id].block
        if TYPE_CHECKING:
            assert coordinator
            assert coordinator.device.blocks

        for block in coordinator.device.blocks:
            if (
                "inputEvent" not in block.sensor_ids
                or "inputEventCnt" not in block.sensor_ids
            ):
                continue

            if not is_block_momentary_input(coordinator.device.settings, block, True):
                continue

            input_id = int(block.channel or 0) + 1

            if BLOCK_EVENT.removal_condition and BLOCK_EVENT.removal_condition(
                coordinator.device.settings, block
            ):
                unique_id = f"{coordinator.mac}-{input_id}"
                async_remove_shelly_entity(hass, EVENT_DOMAIN, unique_id)
            else:
                entities.append(ShellyBlockEvent(coordinator, input_id, BLOCK_EVENT))

    async_add_entities(entities)


class ShellyRpcEvent(CoordinatorEntity[ShellyRpcCoordinator], EventEntity):
    """Represent RPC event entity."""

    _attr_should_poll = False
    entity_description: ShellyRpcEventDescription

    def __init__(
        self,
        coordinator: ShellyRpcCoordinator,
        key: str,
        description: ShellyRpcEventDescription,
    ) -> None:
        """Initialize Shelly entity."""
        super().__init__(coordinator)
        self.input_index = int(key.split(":")[-1])
        self._attr_device_info = DeviceInfo(
            connections={(CONNECTION_NETWORK_MAC, coordinator.mac)}
        )
        self._attr_unique_id = f"{coordinator.mac}-{key}"
        self._attr_name = get_rpc_input_name(coordinator.device, key)
        self.entity_description = description

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_subscribe_input_events(self._async_handle_event)
        )

    @callback
    def _async_handle_event(self, event: dict[str, Any]) -> None:
        """Handle the demo button event."""
        if event["id"] == self.input_index:
            self._trigger_event(event["event"])
            self.async_write_ha_state()


class ShellyBlockEvent(CoordinatorEntity[ShellyBlockCoordinator], EventEntity):
    """Represent Block event entity."""

    _attr_should_poll = False
    entity_description: ShellyBlockEventDescription

    def __init__(
        self,
        coordinator: ShellyBlockCoordinator,
        input_id: int,
        description: ShellyBlockEventDescription,
    ) -> None:
        """Initialize Shelly entity."""
        super().__init__(coordinator)
        self.input_id = input_id
        self._attr_device_info = DeviceInfo(
            connections={(CONNECTION_NETWORK_MAC, coordinator.mac)}
        )
        self._attr_unique_id = f"{coordinator.mac}-input-{input_id}"
        self._attr_name = f"{coordinator.device.name} Input {input_id}"
        self.entity_description = description

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_subscribe_input_events(self._async_handle_event)
        )

    @callback
    def _async_handle_event(self, event: dict[str, Any]) -> None:
        """Handle the demo button event."""
        if event["id"] == self.input_id:
            self._trigger_event(event["event"])
            self.async_write_ha_state()
