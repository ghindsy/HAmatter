"""
Support for Tahoma cover - shutters etc.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/cover.tahoma/
"""
import logging
from datetime import timedelta

from homeassistant.components.cover import CoverDevice
from homeassistant.components.tahoma import (
    DOMAIN as TAHOMA_DOMAIN, TahomaDevice)

DEPENDENCIES = ['tahoma']

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=60)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up Tahoma covers."""
    controller = hass.data[TAHOMA_DOMAIN]['controller']
    devices = []
    for device in hass.data[TAHOMA_DOMAIN]['devices']['cover']:
        devices.append(TahomaCover(device, controller))
    add_devices(devices, True)


class TahomaCover(TahomaDevice, CoverDevice):
    """Representation a Tahoma Cover."""

    def update(self):
        """Update method."""
        self.controller.get_states([self.tahoma_device])

    @property
    def current_cover_position(self):
        """
        Return current position of cover.

        0 is closed, 100 is fully open.
        """
        try:
            position = 100 - \
                self.tahoma_device.active_states['core:ClosureState']
            if position <= 5:
                return 0
            if position >= 95:
                return 100
            return position
        except KeyError:
            return None

    def set_cover_position(self, position, **kwargs):
        """Move the cover to a specific position."""
        self.apply_action('setPosition', 100 - position)

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        if self.current_cover_position is not None:
            return self.current_cover_position == 0

    def open_cover(self, **kwargs):
        """Open the cover."""
        self.apply_action('open')

    def close_cover(self, **kwargs):
        """Close the cover."""
        self.apply_action('close')

    def stop_cover(self, **kwargs):
        """Stop the cover."""
        self.apply_action('stopIdentify')
