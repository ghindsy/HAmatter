"""Device for Zigbee Home Automation."""
import asyncio
from datetime import timedelta
from enum import Enum
import logging
import random
import time
from typing import Any, Dict, List, Optional, Union

from zigpy import types
import zigpy.exceptions
from zigpy.profiles import zha, zll
import zigpy.quirks
from zigpy.zcl.clusters.general import Groups
import zigpy.zdo.types as zdo_types

from homeassistant.core import callback
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import HomeAssistantType

from . import channels, typing as zha_typing
from .const import (
    ATTR_ARGS,
    ATTR_ATTRIBUTE,
    ATTR_AVAILABLE,
    ATTR_CLUSTER_ID,
    ATTR_COMMAND,
    ATTR_COMMAND_TYPE,
    ATTR_DEVICE_TYPE,
    ATTR_ENDPOINT_ID,
    ATTR_IEEE,
    ATTR_LAST_SEEN,
    ATTR_LQI,
    ATTR_MANUFACTURER,
    ATTR_MANUFACTURER_CODE,
    ATTR_MODEL,
    ATTR_NAME,
    ATTR_NWK,
    ATTR_POWER_SOURCE,
    ATTR_QUIRK_APPLIED,
    ATTR_QUIRK_CLASS,
    ATTR_RSSI,
    ATTR_VALUE,
    CLUSTER_COMMAND_SERVER,
    CLUSTER_COMMANDS_CLIENT,
    CLUSTER_COMMANDS_SERVER,
    CLUSTER_TYPE_IN,
    CLUSTER_TYPE_OUT,
    EFFECT_DEFAULT_VARIANT,
    EFFECT_OKAY,
    POWER_BATTERY_OR_UNKNOWN,
    POWER_MAINS_POWERED,
    SIGNAL_AVAILABLE,
    UNKNOWN,
    UNKNOWN_MANUFACTURER,
    UNKNOWN_MODEL,
)
from .helpers import LogMixin

_LOGGER = logging.getLogger(__name__)
_KEEP_ALIVE_INTERVAL = 7200
_UPDATE_ALIVE_INTERVAL = (60, 90)
_CHECKIN_GRACE_PERIODS = 2


class DeviceStatus(Enum):
    """Status of a device."""

    CREATED = 1
    INITIALIZED = 2


class ZHADevice(LogMixin):
    """ZHA Zigbee device object."""

    def __init__(
        self,
        hass: HomeAssistantType,
        zigpy_device: zha_typing.ZigpyDeviceType,
        zha_gateway: zha_typing.ZhaGatewayType,
    ):
        """Initialize the gateway."""
        self.hass: HomeAssistantType = hass
        self._zigpy_device: zha_typing.ZigpyDeviceType = zigpy_device
        self._zha_gateway: zha_typing.ZhaGatewayType = zha_gateway
        self._available: bool = False
        self._available_signal: str = "{}_{}_{}".format(
            self.name, self.ieee, SIGNAL_AVAILABLE
        )
        self._checkins_missed_count: int = 0
        self._unsub = async_dispatcher_connect(
            self.hass, self._available_signal, self.async_initialize
        )
        self.quirk_applied: bool = isinstance(
            self._zigpy_device, zigpy.quirks.CustomDevice
        )
        self.quirk_class: str = "{}.{}".format(
            self._zigpy_device.__class__.__module__,
            self._zigpy_device.__class__.__name__,
        )
        keep_alive_interval: int = random.randint(*_UPDATE_ALIVE_INTERVAL)
        self._available_check = async_track_time_interval(
            self.hass, self._check_available, timedelta(seconds=keep_alive_interval)
        )
        self._ha_device_id: Optional[str] = None
        self.status: DeviceStatus = DeviceStatus.CREATED
        self._channels: zha_typing.ChannelsType = channels.Channels(self)

    @property
    def device_id(self) -> Optional[str]:
        """Return the HA device registry device id."""
        return self._ha_device_id

    def set_device_id(self, device_id: str) -> None:
        """Set the HA device registry device id."""
        self._ha_device_id = device_id

    @property
    def device(self) -> zha_typing.ZigpyDeviceType:
        """Return underlying Zigpy device."""
        return self._zigpy_device

    @property
    def channels(self) -> zha_typing.ChannelsType:
        """Return ZHA channels."""
        return self._channels

    @channels.setter
    def channels(self, value: zha_typing.ChannelsType) -> None:
        """Channels setter."""
        assert isinstance(value, channels.Channels)
        self._channels = value

    @property
    def name(self) -> str:
        """Return device name."""
        return f"{self.manufacturer} {self.model}"

    @property
    def ieee(self) -> zha_typing.ZigpyEUI64Type:
        """Return ieee address for device."""
        return self._zigpy_device.ieee

    @property
    def manufacturer(self) -> str:
        """Return manufacturer for device."""
        if self._zigpy_device.manufacturer is None:
            return UNKNOWN_MANUFACTURER
        return self._zigpy_device.manufacturer

    @property
    def model(self) -> str:
        """Return model for device."""
        if self._zigpy_device.model is None:
            return UNKNOWN_MODEL
        return self._zigpy_device.model

    @property
    def manufacturer_code(self) -> Optional[int]:
        """Return the manufacturer code for the device."""
        if self._zigpy_device.node_desc.is_valid:
            return self._zigpy_device.node_desc.manufacturer_code
        return None

    @property
    def nwk(self) -> int:
        """Return nwk for device."""
        return self._zigpy_device.nwk

    @property
    def lqi(self) -> Optional[int]:
        """Return lqi for device."""
        return self._zigpy_device.lqi

    @property
    def rssi(self) -> Optional[int]:
        """Return rssi for device."""
        return self._zigpy_device.rssi

    @property
    def last_seen(self) -> Optional[float]:
        """Return last_seen for device."""
        return self._zigpy_device.last_seen

    @property
    def is_mains_powered(self) -> Optional[bool]:
        """Return true if device is mains powered."""
        return self._zigpy_device.node_desc.is_mains_powered

    @property
    def device_type(self) -> str:
        """Return the logical device type for the device."""
        node_descriptor = self._zigpy_device.node_desc
        return (
            node_descriptor.logical_type.name if node_descriptor.is_valid else UNKNOWN
        )

    @property
    def power_source(self) -> str:
        """Return the power source for the device."""
        return (
            POWER_MAINS_POWERED if self.is_mains_powered else POWER_BATTERY_OR_UNKNOWN
        )

    @property
    def is_router(self) -> Optional[bool]:
        """Return true if this is a routing capable device."""
        return self._zigpy_device.node_desc.is_router

    @property
    def is_coordinator(self) -> Optional[bool]:
        """Return true if this device represents the coordinator."""
        return self._zigpy_device.node_desc.is_coordinator

    @property
    def is_end_device(self) -> Optional[bool]:
        """Return true if this device is an end device."""
        return self._zigpy_device.node_desc.is_end_device

    @property
    def is_groupable(self) -> bool:
        """Return true if this device has a group cluster."""
        if not self.available:
            return False
        clusters = self.async_get_clusters()
        for cluster_map in clusters.values():
            for clusters in cluster_map.values():
                if Groups.cluster_id in clusters:
                    return True
        return False

    @property
    def skip_configuration(self) -> bool:
        """Return true if the device should not issue configuration related commands."""
        return self._zigpy_device.skip_configuration

    @property
    def gateway(self) -> zha_typing.ZhaGatewayType:
        """Return the gateway for this device."""
        return self._zha_gateway

    @property
    def device_automation_triggers(self) -> Optional[List[dict]]:
        """Return the device automation triggers for this device."""
        if hasattr(self._zigpy_device, "device_automation_triggers"):
            return self._zigpy_device.device_automation_triggers
        return None

    @property
    def available_signal(self) -> str:
        """Signal to use to subscribe to device availability changes."""
        return self._available_signal

    @property
    def available(self) -> bool:
        """Return True if sensor is available."""
        return self._available

    def set_available(self, available: bool) -> None:
        """Set availability from restore and prevent signals."""
        self._available = available

    @classmethod
    def new(
        cls,
        hass: HomeAssistantType,
        zigpy_dev: zha_typing.ZigpyDeviceType,
        gateway: zha_typing.ZhaGatewayType,
        restored: bool = False,
    ):
        """Create new device."""
        zha_dev = cls(hass, zigpy_dev, gateway)
        zha_dev.channels = channels.Channels.new(zha_dev)
        return zha_dev

    async def _check_available(self, *_) -> None:
        if self.last_seen is None:
            self.update_available(False)
            return

        difference = time.time() - self.last_seen
        if difference < _KEEP_ALIVE_INTERVAL:
            self.update_available(True)
            self._checkins_missed_count = 0
            return

        if (
            self._checkins_missed_count >= _CHECKIN_GRACE_PERIODS
            or self.manufacturer == "LUMI"
            or not self._channels.pools
        ):
            self.update_available(False)
            return

        self._checkins_missed_count += 1
        self.debug(
            "Attempting to checkin with device - missed checkins: %s",
            self._checkins_missed_count,
        )
        try:
            pool = self._channels.pools[0]
            basic_ch = pool.all_channels[f"{pool.id}:0x0000"]
        except KeyError:
            self.debug("does not have a mandatory basic cluster")
            self.update_available(False)
            return
        res = await basic_ch.get_attribute_value(ATTR_MANUFACTURER, from_cache=False)
        if res is not None:
            self._checkins_missed_count = 0

    def update_available(self, available: bool) -> None:
        """Set sensor availability."""
        if self._available != available and available:
            # Update the state the first time the device comes online
            async_dispatcher_send(self.hass, self._available_signal, False)
        async_dispatcher_send(
            self.hass, "{}_{}".format(self._available_signal, "entity"), available
        )
        self._available = available

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return a device description for device."""
        ieee = str(self.ieee)
        time_struct = time.localtime(self.last_seen)
        update_time = time.strftime("%Y-%m-%dT%H:%M:%S", time_struct)
        return {
            ATTR_IEEE: ieee,
            ATTR_NWK: self.nwk,
            ATTR_MANUFACTURER: self.manufacturer,
            ATTR_MODEL: self.model,
            ATTR_NAME: self.name or ieee,
            ATTR_QUIRK_APPLIED: self.quirk_applied,
            ATTR_QUIRK_CLASS: self.quirk_class,
            ATTR_MANUFACTURER_CODE: self.manufacturer_code,
            ATTR_POWER_SOURCE: self.power_source,
            ATTR_LQI: self.lqi,
            ATTR_RSSI: self.rssi,
            ATTR_LAST_SEEN: update_time,
            ATTR_AVAILABLE: self.available,
            ATTR_DEVICE_TYPE: self.device_type,
        }

    async def async_configure(self) -> None:
        """Configure the device."""
        self.debug("started configuration")
        await self._channels.async_configure()
        self.debug("completed configuration")
        entry = self.gateway.zha_storage.async_create_or_update(self)
        self.debug("stored in registry: %s", entry)

        if self._channels.identify_ch is not None:
            await self._channels.identify_ch.trigger_effect(
                EFFECT_OKAY, EFFECT_DEFAULT_VARIANT
            )

    async def async_initialize(self, from_cache: bool = False) -> None:
        """Initialize channels."""
        self.debug("started initialization")
        await self._channels.async_initialize(from_cache)
        self.debug("power source: %s", self.power_source)
        self.status = DeviceStatus.INITIALIZED
        self.debug("completed initialization")

    @callback
    def async_unsub_dispatcher(self) -> None:
        """Unsubscribe the dispatcher."""
        self._unsub()

    @callback
    def async_update_last_seen(self, last_seen: float) -> None:
        """Set last seen on the zigpy device."""
        self._zigpy_device.last_seen = last_seen

    @callback
    def async_get_info(self) -> Dict[str, Any]:
        """Get ZHA device information."""
        device_info = {}
        device_info.update(self.device_info)
        device_info["entities"] = [
            {
                "entity_id": entity_ref.reference_id,
                ATTR_NAME: entity_ref.device_info[ATTR_NAME],
            }
            for entity_ref in self.gateway.device_registry[self.ieee]
        ]
        reg_device = self.gateway.ha_device_registry.async_get(self.device_id)
        if reg_device is not None:
            device_info["user_given_name"] = reg_device.name_by_user
            device_info["device_reg_id"] = reg_device.id
            device_info["area_id"] = reg_device.area_id
        return device_info

    @callback
    def async_get_clusters(
        self,
    ) -> Dict[int, Dict[str, Dict[int, zha_typing.ZigpyClusterType]]]:
        """Get all clusters for this device."""
        return {
            ep_id: {
                CLUSTER_TYPE_IN: endpoint.in_clusters,
                CLUSTER_TYPE_OUT: endpoint.out_clusters,
            }
            for (ep_id, endpoint) in self._zigpy_device.endpoints.items()
            if ep_id != 0
        }

    @callback
    def async_get_std_clusters(
        self,
    ) -> Dict[int, Dict[str, Dict[int, zha_typing.ZigpyClusterType]]]:
        """Get ZHA and ZLL clusters for this device."""

        return {
            ep_id: {
                CLUSTER_TYPE_IN: endpoint.in_clusters,
                CLUSTER_TYPE_OUT: endpoint.out_clusters,
            }
            for (ep_id, endpoint) in self._zigpy_device.endpoints.items()
            if ep_id != 0 and endpoint.profile_id in (zha.PROFILE_ID, zll.PROFILE_ID)
        }

    @callback
    def async_get_cluster(
        self, endpoint_id: int, cluster_id: int, cluster_type: str = CLUSTER_TYPE_IN
    ) -> zha_typing.ZigpyClusterType:
        """Get zigbee cluster from this entity."""
        clusters = self.async_get_clusters()
        return clusters[endpoint_id][cluster_type][cluster_id]

    @callback
    def async_get_cluster_attributes(
        self, endpoint_id: int, cluster_id: int, cluster_type: str = CLUSTER_TYPE_IN
    ) -> Optional[Dict[int, Any]]:
        """Get zigbee attributes for specified cluster."""
        cluster = self.async_get_cluster(endpoint_id, cluster_id, cluster_type)
        if cluster is None:
            return None
        return cluster.attributes

    @callback
    def async_get_cluster_commands(
        self, endpoint_id: int, cluster_id: int, cluster_type: str = CLUSTER_TYPE_IN
    ) -> Optional[Dict[str, Dict[int, Any]]]:
        """Get zigbee commands for specified cluster."""
        cluster = self.async_get_cluster(endpoint_id, cluster_id, cluster_type)
        if cluster is None:
            return None
        return {
            CLUSTER_COMMANDS_CLIENT: cluster.client_commands,
            CLUSTER_COMMANDS_SERVER: cluster.server_commands,
        }

    async def write_zigbee_attribute(
        self,
        endpoint_id: int,
        cluster_id: int,
        attribute: Union[int, str],
        value: Any,
        cluster_type: str = CLUSTER_TYPE_IN,
        manufacturer: int = None,
    ) -> Any:
        """Write a value to a zigbee attribute for a cluster in this entity."""
        cluster = self.async_get_cluster(endpoint_id, cluster_id, cluster_type)
        if cluster is None:
            return None

        try:
            response = await cluster.write_attributes(
                {attribute: value}, manufacturer=manufacturer
            )
            self.debug(
                "set: %s for attr: %s to cluster: %s for ept: %s - res: %s",
                value,
                attribute,
                cluster_id,
                endpoint_id,
                response,
            )
            return response
        except zigpy.exceptions.DeliveryError as exc:
            self.debug(
                "failed to set attribute: %s %s %s %s %s",
                f"{ATTR_VALUE}: {value}",
                f"{ATTR_ATTRIBUTE}: {attribute}",
                f"{ATTR_CLUSTER_ID}: {cluster_id}",
                f"{ATTR_ENDPOINT_ID}: {endpoint_id}",
                exc,
            )
            return None

    async def issue_cluster_command(
        self,
        endpoint_id: int,
        cluster_id: int,
        command: int,
        command_type: str,
        *args,
        cluster_type: str = CLUSTER_TYPE_IN,
        manufacturer: int = None,
    ) -> Any:
        """Issue a command against specified zigbee cluster on this entity."""
        cluster = self.async_get_cluster(endpoint_id, cluster_id, cluster_type)
        if cluster is None:
            return None
        if command_type == CLUSTER_COMMAND_SERVER:
            response = await cluster.command(
                command, *args, manufacturer=manufacturer, expect_reply=True
            )
        else:
            response = await cluster.client_command(command, *args)

        self.debug(
            "Issued cluster command: %s %s %s %s %s %s %s",
            f"{ATTR_CLUSTER_ID}: {cluster_id}",
            f"{ATTR_COMMAND}: {command}",
            f"{ATTR_COMMAND_TYPE}: {command_type}",
            f"{ATTR_ARGS}: {args}",
            f"{ATTR_CLUSTER_ID}: {cluster_type}",
            f"{ATTR_MANUFACTURER}: {manufacturer}",
            f"{ATTR_ENDPOINT_ID}: {endpoint_id}",
        )
        return response

    async def async_add_to_group(self, group_id: int) -> None:
        """Add this device to the provided zigbee group."""
        await self._zigpy_device.add_to_group(group_id)

    async def async_remove_from_group(self, group_id: int) -> None:
        """Remove this device from the provided zigbee group."""
        await self._zigpy_device.remove_from_group(group_id)

    async def async_bind_to_group(self, group_id: int, cluster_bindings) -> None:
        """Directly bind this device to a group for the given clusters."""
        await self._async_group_binding_operation(
            group_id, zdo_types.ZDOCmd.Bind_req, cluster_bindings
        )

    async def async_unbind_from_group(self, group_id: int, cluster_bindings) -> None:
        """Unbind this device from a group for the given clusters."""
        await self._async_group_binding_operation(
            group_id, zdo_types.ZDOCmd.Unbind_req, cluster_bindings
        )

    async def _async_group_binding_operation(
        self, group_id: int, operation: zha_typing.ZigpyZDOCommandType, cluster_bindings
    ) -> None:
        """Create or remove a direct zigbee binding between a device and a group."""

        zdo = self._zigpy_device.zdo
        op_msg = "0x%04x: %s %s, ep: %s, cluster: %s to group: 0x%04x"
        destination_address = zdo_types.MultiAddress()
        destination_address.addrmode = types.uint8_t(1)
        destination_address.nwk = types.uint16_t(group_id)

        tasks = []

        for cluster_binding in cluster_bindings:
            if cluster_binding.endpoint_id == 0:
                continue
            if (
                cluster_binding.id
                in self._zigpy_device.endpoints[
                    cluster_binding.endpoint_id
                ].out_clusters
            ):
                op_params = (
                    self.nwk,
                    operation.name,
                    str(self.ieee),
                    cluster_binding.endpoint_id,
                    cluster_binding.id,
                    group_id,
                )
                zdo.debug("processing " + op_msg, *op_params)
                tasks.append(
                    (
                        zdo.request(
                            operation,
                            self.ieee,
                            cluster_binding.endpoint_id,
                            cluster_binding.id,
                            destination_address,
                        ),
                        op_msg,
                        op_params,
                    )
                )
        res = await asyncio.gather(*(t[0] for t in tasks), return_exceptions=True)
        for outcome, log_msg in zip(res, tasks):
            if isinstance(outcome, Exception):
                fmt = log_msg[1] + " failed: %s"
            else:
                fmt = log_msg[1] + " completed: %s"
            zdo.debug(fmt, *(log_msg[2] + (outcome,)))

    def log(self, level, msg, *args):
        """Log a message."""
        msg = f"[%s](%s): {msg}"
        args = (self.nwk, self.model) + args
        _LOGGER.log(level, msg, *args)
