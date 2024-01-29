"""Closures cluster handlers module for Zigbee Home Automation."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import zigpy.zcl
from zigpy.zcl.clusters.closures import DoorLock, Shade, WindowCovering

from homeassistant.core import callback

from .. import registries
from ..const import REPORT_CONFIG_IMMEDIATE, SIGNAL_ATTR_UPDATED
from . import AttrReportConfig, ClientClusterHandler, ClusterHandler

if TYPE_CHECKING:
    from ..endpoint import Endpoint


@registries.ZIGBEE_CLUSTER_HANDLER_REGISTRY.register(DoorLock.cluster_id)
class DoorLockClusterHandler(ClusterHandler):
    """Door lock cluster handler."""

    _value_attribute = 0
    REPORT_CONFIG = (
        AttrReportConfig(
            attr=DoorLock.AttributeDefs.lock_state.name,
            config=REPORT_CONFIG_IMMEDIATE,
        ),
    )

    async def async_update(self):
        """Retrieve latest state."""
        result = await self.read_attribute(
            DoorLock.AttributeDefs.lock_state.name, from_cache=True
        )
        self.async_send_signal(
            f"{self.unique_id}_{SIGNAL_ATTR_UPDATED}",
            DoorLock.AttributeDefs.lock_state.id,
            DoorLock.AttributeDefs.lock_state.name,
            result,
        )

    @callback
    def cluster_command(self, tsn, command_id, args):
        """Handle a cluster command received on this cluster."""

        if (
            self._cluster.client_commands is None
            or self._cluster.client_commands.get(command_id) is None
        ):
            return

        command_name = self._cluster.client_commands[command_id].name

        if command_name == "operation_event_notification":
            self.zha_send_event(
                command_name,
                {
                    "source": args[0].name,
                    "operation": args[1].name,
                    "code_slot": (args[2] + 1),  # start code slots at 1
                },
            )

    @callback
    def attribute_updated(self, attrid: int, value: Any, _: Any) -> None:
        """Handle attribute update from lock cluster."""
        attr_name = self._get_attribute_name(attrid)
        self.debug(
            "Attribute report '%s'[%s] = %s", self.cluster.name, attr_name, value
        )
        if attrid == self._value_attribute:
            self.async_send_signal(
                f"{self.unique_id}_{SIGNAL_ATTR_UPDATED}", attrid, attr_name, value
            )

    async def async_set_user_code(self, code_slot: int, user_code: str) -> None:
        """Set the user code for the code slot."""

        await self.set_pin_code(
            code_slot - 1,  # start code slots at 1, Zigbee internals use 0
            DoorLock.UserStatus.Enabled,
            DoorLock.UserType.Unrestricted,
            user_code,
        )

    async def async_enable_user_code(self, code_slot: int) -> None:
        """Enable the code slot."""

        await self.set_user_status(code_slot - 1, DoorLock.UserStatus.Enabled)

    async def async_disable_user_code(self, code_slot: int) -> None:
        """Disable the code slot."""

        await self.set_user_status(code_slot - 1, DoorLock.UserStatus.Disabled)

    async def async_get_user_code(self, code_slot: int) -> int:
        """Get the user code from the code slot."""

        result = await self.get_pin_code(code_slot - 1)
        return result

    async def async_clear_user_code(self, code_slot: int) -> None:
        """Clear the code slot."""

        await self.clear_pin_code(code_slot - 1)

    async def async_clear_all_user_codes(self) -> None:
        """Clear all code slots."""

        await self.clear_all_pin_codes()

    async def async_set_user_type(self, code_slot: int, user_type: str) -> None:
        """Set user type."""

        await self.set_user_type(code_slot - 1, user_type)

    async def async_get_user_type(self, code_slot: int) -> str:
        """Get user type."""

        result = await self.get_user_type(code_slot - 1)
        return result


@registries.ZIGBEE_CLUSTER_HANDLER_REGISTRY.register(Shade.cluster_id)
class ShadeClusterHandler(ClusterHandler):
    """Shade cluster handler."""


@registries.CLIENT_CLUSTER_HANDLER_REGISTRY.register(WindowCovering.cluster_id)
class WindowCoveringClientClusterHandler(ClientClusterHandler):
    """Window client cluster handler."""


@registries.BINDABLE_CLUSTERS.register(WindowCovering.cluster_id)
@registries.ZIGBEE_CLUSTER_HANDLER_REGISTRY.register(WindowCovering.cluster_id)
class WindowCoveringClusterHandler(ClusterHandler):
    """Window cluster handler."""

    _value_attribute_lift = (
        WindowCovering.AttributeDefs.current_position_lift_percentage.id
    )
    _value_attribute_tilt = (
        WindowCovering.AttributeDefs.current_position_tilt_percentage.id
    )
    REPORT_CONFIG = (
        AttrReportConfig(
            attr="current_position_lift_percentage", config=REPORT_CONFIG_IMMEDIATE
        ),
        AttrReportConfig(
            attr="current_position_tilt_percentage", config=REPORT_CONFIG_IMMEDIATE
        ),
    )

    def __init__(self, cluster: zigpy.zcl.Cluster, endpoint: Endpoint) -> None:
        """Initialize WindowCovering cluster handler."""
        super().__init__(cluster, endpoint)

        if self.cluster.endpoint.model == "lumi.curtain.agl001":
            self.ZCL_INIT_ATTRS = self.ZCL_INIT_ATTRS.copy()
            self.ZCL_INIT_ATTRS["window_covering_mode"] = True

    async def async_update(self):
        """Retrieve latest state."""
        await self.read_attributes(
            ["current_position_lift_percentage", "current_position_tilt_percentage"],
            ignore_failures=True,
        )

    @callback
    def attribute_updated(self, attrid: int, value: Any, _: Any) -> None:
        """Handle attribute update from window_covering cluster."""
        attr_name = self._get_attribute_name(attrid)
        self.debug(
            "Attribute report '%s'[%s] = %s", self.cluster.name, attr_name, value
        )
        if attrid in (self._value_attribute_lift, self._value_attribute_tilt):
            self.async_send_signal(
                f"{self.unique_id}_{SIGNAL_ATTR_UPDATED}", attrid, attr_name, value
            )
