"""
Support for displaying IPs banned by fail2ban.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.fail2ban/
"""
import os
import asyncio
import logging

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
import homeassistant.util.dt as dt_util
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_NAME, CONF_SCAN_INTERVAL, CONF_FILE_PATH
)
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

CONF_JAILS = 'jails'

DEFAULT_NAME = 'fail2ban'
DEFAULT_LOG = '/var/log/fail2ban.log'
DEFAULT_SCAN_INTERVAL = 120

STATE_CURRENT_BANS = 'current_bans'
STATE_ALL_BANS = 'total_bans'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_JAILS, default=[]):
        vol.All(cv.ensure_list, vol.Length(min=1)),
    vol.Optional(CONF_FILE_PATH, default=DEFAULT_LOG): cv.isfile,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL):
        cv.positive_timedelta,
})


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up the fail2ban sensor."""
    name = config.get(CONF_NAME)
    jails = config.get(CONF_JAILS)
    scan_interval = config.get(CONF_SCAN_INTERVAL)
    log_file = config.get(CONF_FILE_PATH)

    device_list = []
    log_parser = BanLogParser(scan_interval, log_file)
    for jail in jails:
        device_list.append(BanSensor(name, jail, log_parser))

    async_add_devices(device_list, True)


class BanSensor(Entity):
    """Implementation of a fail2ban sensor."""

    def __init__(self, name, jail, log_parser):
        """Initialize the sensor."""
        self._name = '{} {}'.format(name, jail)
        self.jail = jail
        self.ban_dict = {STATE_CURRENT_BANS: [], STATE_ALL_BANS: []}
        self.last_ban = None
        self.log_parser = log_parser
        _LOGGER.debug("Setting up jail %s", self.jail)

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state_attributes(self):
        """Return the state attributes of the fail2ban sensor."""
        return self.ban_dict

    @property
    def state(self):
        """Return the most recently banned IP Address."""
        return self.last_ban

    def update(self):
        """Update the list of banned ips."""
        if self.log_parser.timer():
            self.log_parser.read_log(self.jail)

        self.last_ban = 'None'
        if self.log_parser.data:
            for entry in self.log_parser.data:
                _LOGGER.debug(entry)
                split_entry = entry.split()

                if 'Ban' in split_entry:
                    ip_index = split_entry.index('Ban') + 1
                    this_ban = split_entry[ip_index]
                    if this_ban not in self.ban_dict[STATE_CURRENT_BANS]:
                        self.last_ban = this_ban
                        self.ban_dict[STATE_CURRENT_BANS].append(this_ban)
                    if this_ban not in self.ban_dict[STATE_ALL_BANS]:
                        self.ban_dict[STATE_ALL_BANS].append(this_ban)
                    if len(self.ban_dict[STATE_ALL_BANS]) > 10:
                        self.ban_dict[STATE_ALL_BANS].pop(0)

                elif 'Unban' in split_entry:
                    ip_index = split_entry.index('Unban') + 1
                    this_unban = split_entry[ip_index]
                    if this_unban in self.ban_dict[STATE_CURRENT_BANS]:
                        self.ban_dict[STATE_CURRENT_BANS].remove(this_unban)
                    if self.last_ban == this_unban:
                        self.last_ban = 'None'


class BanLogParser(object):
    """Class to parse fail2ban logs."""

    def __init__(self, interval, log_file):
        """Initialize the parser."""
        self.interval = interval
        self.log_file = log_file
        self.data = list()
        self.last_update = dt_util.now()

    def timer(self):
        """Check if we are allowed to update."""
        boundary = dt_util.now() - self.interval
        if boundary > self.last_update:
            self.last_update = dt_util.now()
            return True

    def read_log(self, jail):
        """Read the fail2ban log and find entries for jail."""
        self.data = list()
        try:
            with open(self.log_file, 'r', encoding='utf-8') as file_data:
                for line in file_data:
                    if jail in line and 'fail2ban.actions' in line:
                        self.data.append(line)
        except (IndexError, FileNotFoundError, IsADirectoryError,
                UnboundLocalError):
            _LOGGER.warning("File not present: %s",
                            os.path.basename(self.log_file))
