"""
Support for BMW cars with BMW ConnectedDrive.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/lock.bmw_connected_drive/
"""
import asyncio
import logging

from homeassistant.components.bmw_connected_drive import DOMAIN as BMW_DOMAIN
from homeassistant.components.lock import LockDevice
from homeassistant.const import STATE_LOCKED, STATE_UNLOCKED

DEPENDENCIES = ['bmw_connected_drive']

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the BMW Connected Drive lock."""
    accounts = hass.data[BMW_DOMAIN]
    _LOGGER.debug('Found BMW accounts: %s',
                  ', '.join([a.name for a in accounts]))
    devices = []
    for account in accounts:
        for vehicle in account.account.vehicles:
            device = BMWLock(account, vehicle, 'lock', 'BMW lock')
            devices.append(device)
    add_devices(devices, True)


class BMWLock(LockDevice):
    """Representation of a BMW vehicle lock."""

    def __init__(self, account, vehicle, attribute: str, sensor_name):
        """Initialize the lock."""
        self._account = account
        self._vehicle = vehicle
        self._attribute = attribute
        self._name = sensor_name
        self._state = None

    @property
    def should_poll(self):
        """Do not poll this class.

        Updates are triggered from BMWConnectedDriveAccount.
        """
        return False

    @property
    def name(self):
        """Return the name of the lock."""
        return self._name

    @property
    def device_state_attributes(self):
        """Return the state attributes of the lock."""
        vehicle_state = self._vehicle.state
        return {
            'car': self._vehicle.modelName,
            'door_lock_state': vehicle_state.door_lock_state.value
        }

    @property
    def is_locked(self):
        """Return true if lock is locked."""
        return self._state == STATE_LOCKED

    def lock(self, **kwargs):
        """Lock the car."""
        _LOGGER.debug("%s: locking doors", self._vehicle.modelName)
        # Optimistic state set here because it takes some time before the
        # update callback response
        self._state = STATE_LOCKED
        self.schedule_update_ha_state()
        self._vehicle.remote_services.trigger_remote_door_lock()

    def unlock(self, **kwargs):
        """Unlock the car."""
        _LOGGER.debug("%s: unlocking doors", self._vehicle.modelName)
        # Optimistic state set here because it takes some time before the
        # update callback response
        self._state = STATE_UNLOCKED
        self.schedule_update_ha_state()
        self._vehicle.remote_services.trigger_remote_door_unlock()

    def update(self):
        """Update state of the lock."""
        _LOGGER.debug("%s: updating data for %s", self._vehicle.modelName,
                      self._attribute)
        vehicle_state = self._vehicle.state

        # Possible values: LOCKED, SECURED, SELECTIVELOCKED, UNLOCKED
        self._state = (STATE_LOCKED if vehicle_state.door_lock_state.value
                       in ('LOCKED', 'SECURED') else STATE_UNLOCKED)

    def update_callback(self):
        """Schedule a state update."""
        self.schedule_update_ha_state(True)

    @asyncio.coroutine
    def async_added_to_hass(self):
        """Add callback after being added to hass.

        Show latest data after startup.
        """
        self._account.add_update_listener(self.update_callback)
