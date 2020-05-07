"""Track devices using UniFi controllers."""
from datetime import timedelta
import logging

from aiounifi.api import SOURCE_DATA, SOURCE_EVENT
from aiounifi.events import (
    WIRED_CLIENT_CONNECTED,
    WIRELESS_CLIENT_CONNECTED,
    WIRELESS_CLIENT_ROAM,
    WIRELESS_CLIENT_ROAMRADIO,
)

from homeassistant.components.device_tracker import DOMAIN
from homeassistant.components.device_tracker.config_entry import ScannerEntity
from homeassistant.components.device_tracker.const import SOURCE_TYPE_ROUTER
from homeassistant.core import callback
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_track_point_in_utc_time
import homeassistant.util.dt as dt_util

from .const import ATTR_MANUFACTURER, DOMAIN as UNIFI_DOMAIN
from .unifi_client import UniFiClient
from .unifi_entity_base import UniFiBase

LOGGER = logging.getLogger(__name__)

CLIENT_TRACKER = "client"
DEVICE_TRACKER = "device"

CLIENT_CONNECTED_ATTRIBUTES = [
    "_is_guest_by_uap",
    "ap_mac",
    "authorized",
    "essid",
    "ip",
    "is_11r",
    "is_guest",
    "noted",
    "qos_policy_applied",
    "radio",
    "radio_proto",
    "vlan",
]

CLIENT_STATIC_ATTRIBUTES = [
    "hostname",
    "mac",
    "name",
    "oui",
]

WIRED_CONNECTION = (WIRED_CLIENT_CONNECTED,)
WIRELESS_CONNECTION = (
    WIRELESS_CLIENT_CONNECTED,
    WIRELESS_CLIENT_ROAM,
    WIRELESS_CLIENT_ROAMRADIO,
)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up device tracker for UniFi component."""
    controller = hass.data[UNIFI_DOMAIN][config_entry.entry_id]
    controller.entities[DOMAIN] = {CLIENT_TRACKER: set(), DEVICE_TRACKER: set()}

    @callback
    def items_added(
        clients: set = controller.api.clients, devices: set = controller.api.devices
    ) -> None:
        """Update the values of the controller."""
        if controller.option_track_clients:
            add_client_entities(controller, async_add_entities, clients)

        if controller.option_track_devices:
            add_device_entities(controller, async_add_entities, devices)

    for signal in (controller.signal_update, controller.signal_options_update):
        controller.listeners.append(async_dispatcher_connect(hass, signal, items_added))

    items_added()


@callback
def add_client_entities(controller, async_add_entities, clients):
    """Add new client tracker entities from the controller."""
    trackers = []

    for mac in clients:
        if mac in controller.entities[DOMAIN][UniFiClientTracker.TYPE]:
            continue

        client = controller.api.clients[mac]

        if mac not in controller.wireless_clients:
            if not controller.option_track_wired_clients:
                continue
        elif (
            client.essid
            and controller.option_ssid_filter
            and client.essid not in controller.option_ssid_filter
        ):
            continue

        trackers.append(UniFiClientTracker(client, controller))

    if trackers:
        async_add_entities(trackers)


@callback
def add_device_entities(controller, async_add_entities, devices):
    """Add new device tracker entities from the controller."""
    trackers = []

    for mac in devices:
        if mac in controller.entities[DOMAIN][UniFiDeviceTracker.TYPE]:
            continue

        device = controller.api.devices[mac]
        trackers.append(UniFiDeviceTracker(device, controller))

    if trackers:
        async_add_entities(trackers)


class UniFiClientTracker(UniFiClient, ScannerEntity):
    """Representation of a network client."""

    DOMAIN = DOMAIN
    TYPE = CLIENT_TRACKER

    def __init__(self, client, controller):
        """Set up tracked client."""
        super().__init__(client, controller)

        self.schedule_update = False
        self.cancel_scheduled_update = None
        self._is_connected = False
        if self.client.last_seen:
            self._is_connected = (
                self.is_wired == self.client.is_wired
                and dt_util.utcnow()
                - dt_util.utc_from_timestamp(float(self.client.last_seen))
                < self.controller.option_detection_time
            )
            if self._is_connected:
                self.schedule_update = True

    @callback
    def async_update_callback(self) -> None:
        """Update the clients state."""

        @callback
        def _make_disconnected(now):
            """Mark client as disconnected."""
            self._is_connected = False
            self.cancel_scheduled_update = None
            self.async_write_ha_state()

        if self.client.last_updated == SOURCE_EVENT:

            if (self.is_wired and self.client.event.event in WIRED_CONNECTION) or (
                not self.is_wired and self.client.event.event in WIRELESS_CONNECTION
            ):
                self._is_connected = True
                self.schedule_update = False
                if self.cancel_scheduled_update:
                    self.cancel_scheduled_update()
                    self.cancel_scheduled_update = None

            # Ignore extra scheduled update from wired bug
            elif not self.cancel_scheduled_update:
                self.schedule_update = True

        elif not self.client.event and self.client.last_updated == SOURCE_DATA:

            if self.is_wired == self.client.is_wired:
                self._is_connected = True
                self.schedule_update = True

        if self.schedule_update:
            self.schedule_update = False

            if self.cancel_scheduled_update:
                self.cancel_scheduled_update()

            self.cancel_scheduled_update = async_track_point_in_utc_time(
                self.hass,
                _make_disconnected,
                dt_util.utcnow() + self.controller.option_detection_time,
            )

        super().async_update_callback()

    @property
    def is_connected(self):
        """Return true if the client is connected to the network."""
        if (
            not self.is_wired
            and self.client.essid
            and self.controller.option_ssid_filter
            and self.client.essid not in self.controller.option_ssid_filter
        ):
            return False

        return self._is_connected

    @property
    def source_type(self):
        """Return the source type of the client."""
        return SOURCE_TYPE_ROUTER

    @property
    def unique_id(self) -> str:
        """Return a unique identifier for this client."""
        return f"{self.client.mac}-{self.controller.site}"

    @property
    def device_state_attributes(self):
        """Return the client state attributes."""
        attributes = {}

        attributes["is_wired"] = self.is_wired

        for variable in CLIENT_STATIC_ATTRIBUTES + CLIENT_CONNECTED_ATTRIBUTES:
            if variable in self.client.raw:
                if not self.is_connected and variable in CLIENT_CONNECTED_ATTRIBUTES:
                    continue
                attributes[variable] = self.client.raw[variable]

        return attributes

    async def options_updated(self) -> None:
        """Config entry options are updated, remove entity if option is disabled."""
        if not self.controller.option_track_clients:
            await self.async_remove()

        elif self.is_wired:
            if not self.controller.option_track_wired_clients:
                await self.async_remove()

        else:
            if (
                self.controller.option_ssid_filter
                and self.client.essid not in self.controller.option_ssid_filter
            ):
                await self.async_remove()


class UniFiDeviceTracker(UniFiBase, ScannerEntity):
    """Representation of a network infrastructure device."""

    DOMAIN = DOMAIN
    TYPE = DEVICE_TRACKER

    def __init__(self, device, controller):
        """Set up tracked device."""
        self.device = device
        super().__init__(controller)

        self._is_connected = self.device.state == 1
        self.cancel_scheduled_update = None

    @property
    def mac(self):
        """Return MAC of device."""
        return self.device.mac

    async def async_added_to_hass(self):
        """Subscribe to device events."""
        await super().async_added_to_hass()
        self.device.register_callback(self.async_update_callback)

    async def async_will_remove_from_hass(self) -> None:
        """Disconnect device object when removed."""
        await super().async_will_remove_from_hass()
        self.device.remove_callback(self.async_update_callback)

    @callback
    def async_update_callback(self):
        """Update the devices' state."""

        @callback
        def _no_heartbeat(now):
            """No heart beat by device."""
            self._is_connected = False
            self.cancel_scheduled_update = None
            self.async_write_ha_state()

        if self.device.last_updated == SOURCE_DATA:
            self._is_connected = True

            if self.cancel_scheduled_update:
                self.cancel_scheduled_update()

            self.cancel_scheduled_update = async_track_point_in_utc_time(
                self.hass,
                _no_heartbeat,
                dt_util.utcnow() + timedelta(seconds=self.device.next_interval + 10),
            )

        super().async_update_callback()

    @property
    def is_connected(self):
        """Return true if the device is connected to the network."""
        return self._is_connected

    @property
    def source_type(self):
        """Return the source type of the device."""
        return SOURCE_TYPE_ROUTER

    @property
    def name(self) -> str:
        """Return the name of the device."""
        return self.device.name or self.device.model

    @property
    def unique_id(self) -> str:
        """Return a unique identifier for this device."""
        return self.device.mac

    @property
    def available(self) -> bool:
        """Return if controller is available."""
        return not self.device.disabled and self.controller.available

    @property
    def device_info(self):
        """Return a device description for device registry."""
        info = {
            "connections": {(CONNECTION_NETWORK_MAC, self.device.mac)},
            "manufacturer": ATTR_MANUFACTURER,
            "model": self.device.model,
            "sw_version": self.device.version,
        }

        if self.device.name:
            info["name"] = self.device.name

        return info

    @property
    def device_state_attributes(self):
        """Return the device state attributes."""
        if self.device.state == 0:
            return {}

        attributes = {}

        if self.device.has_fan:
            attributes["fan_level"] = self.device.fan_level

        if self.device.overheating:
            attributes["overheating"] = self.device.overheating

        if self.device.upgradable:
            attributes["upgradable"] = self.device.upgradable

        return attributes

    async def options_updated(self) -> None:
        """Config entry options are updated, remove entity if option is disabled."""
        if not self.controller.option_track_devices:
            await self.async_remove()
