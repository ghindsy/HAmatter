"""
Support for displaying IPs banned by fail2ban.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.fail2ban/
"""
import os
import logging

import re
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_NAME, CONF_FILE_PATH
)
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

CONF_JAILS = 'jails'

DEFAULT_NAME = 'fail2ban'
DEFAULT_LOG = '/var/log/fail2ban.log'
SCAN_INTERVAL = timedelta(seconds=120)
DEFAULT_UNITS = 'ip'

STATE_LAST_BAN = 'last_ban'
STATE_CURRENT_BANS = 'current_bans'
STATE_ALL_BANS = 'total_bans'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_JAILS): vol.All(cv.ensure_list, vol.Length(min=1)),
    vol.Optional(CONF_FILE_PATH): cv.isfile,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})


async def async_setup_platform(hass, config, async_add_entities,
                               discovery_info=None):
    """Set up the fail2ban sensor."""
    name = config.get(CONF_NAME)
    jails = config.get(CONF_JAILS)
    log_file = config.get(CONF_FILE_PATH, DEFAULT_LOG)

    device_list = []
    log_parser = BanLogParser(log_file)
    for jail in jails:
        device_list.append(BanSensor(name, jail, log_parser))

    async_add_entities(device_list, True)


class BanSensor(Entity):
    """Implementation of a fail2ban sensor."""

    def __init__(self, name, jail, log_parser):
        """Initialize the sensor."""
        self._name = '{} {}'.format(name, jail)
        self.jail = jail
        self.ban_dict = {STATE_LAST_BAN: None,
                         STATE_CURRENT_BANS: [], STATE_ALL_BANS: []}
        self.number = 0
        self.log_parser = log_parser
        self.log_parser.ip_regex[self.jail] = re.compile(
            r"\[{}\]\s*(Ban|Unban) (.*)".format(re.escape(self.jail))
        )
        _LOGGER.info("Setting up jail %s", self.jail)
        _LOGGER.debug("Regex: %s",
                      str(self.log_parser.ip_regex[self.jail]))

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
        """Return the number of currently banned IP Address."""
        return self.number

    @property
    def unit_of_measurement(self):
        """Return the unit_of_measurement of the device."""
        return DEFAULT_UNITS

    def update(self):
        """Update the list of banned ips."""
        self.log_parser.read_log(self.jail)

        if self.log_parser.data and self.jail in self.log_parser.data:
            for entry in self.log_parser.data[self.jail]:
                current_ip = entry[1]
                if entry[0] == 'Ban':
                    if current_ip not in self.ban_dict[STATE_CURRENT_BANS]:
                        self.ban_dict[STATE_CURRENT_BANS].append(current_ip)
                        self.ban_dict[STATE_LAST_BAN] = current_ip
                    if current_ip not in self.ban_dict[STATE_ALL_BANS]:
                        self.ban_dict[STATE_ALL_BANS].append(current_ip)
                    if len(self.ban_dict[STATE_ALL_BANS]) > 1000:
                        self.ban_dict[STATE_ALL_BANS].pop(0)

                elif entry[0] == 'Unban':
                    if current_ip in self.ban_dict[STATE_CURRENT_BANS]:
                        self.ban_dict[STATE_CURRENT_BANS].remove(current_ip)

        if self.ban_dict[STATE_CURRENT_BANS]:
            self.number = len(self.ban_dict[STATE_CURRENT_BANS])
        else:
            self.number = 0


class BanLogParser:
    """Class to parse fail2ban logs."""

    def __init__(self, log_file):
        """Initialize the parser."""
        self.log_file = log_file
        self.data = dict()
        self.ip_regex = dict()

    def read_log(self, jail):
        """Read the fail2ban log and find entries for jail."""
        self.data[jail] = list()
        try:
            with open(self.log_file, 'r', encoding='utf-8') as file_data:
                self.data[jail] = self.ip_regex[jail].findall(file_data.read())
                _LOGGER.debug("Parsed log file for jail : %s, %d results.",
                              jail, len(self.data[jail])
                              if self.data and jail in self.data else 0)

        except (IndexError, FileNotFoundError, IsADirectoryError,
                UnboundLocalError):
            _LOGGER.warning("File not present: %s",
                            os.path.basename(self.log_file))
