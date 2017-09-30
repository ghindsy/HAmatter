"""
Support for BT Home Hub 5.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/device_tracker.bt_home_hub_5/
"""
import logging
import re
import xml.etree.ElementTree as ET
import json
from urllib.parse import unquote

import requests
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.device_tracker import (
    DOMAIN, PLATFORM_SCHEMA, DeviceScanner)
from homeassistant.const import CONF_HOST

_LOGGER = logging.getLogger(__name__)
_MAC_REGEX = re.compile(r'([0-9a-f]{2}\:){5}[0-9a-f]{2}')

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string
})


# pylint: disable=unused-argument
def get_scanner(hass, config):
    """Return a BT Home Hub 5 scanner if successful."""
    scanner = BTHomeHub5DeviceScanner(config[DOMAIN])

    return scanner if scanner.success_init else None


class BTHomeHub5DeviceScanner(DeviceScanner):
    """This class queries a BT Home Hub 5."""

    def __init__(self, config):
        """Initialise the scanner."""
        _LOGGER.info("Initialising BT Home Hub 5")
        self.host = config.get(CONF_HOST, '192.168.1.254')
        self.last_results = {}
        self.url = 'http://{}/index.cgi?active_page=9098'.format(self.host)

        # Test the router is accessible
        data = _get_homehub_data(self.url)
        self.success_init = data is not None

    def scan_devices(self):
        """Scan for new devices and return a list with found device IDs."""
        self._update_info()

        return (device for device in self.last_results)

    def get_device_name(self, device):
        """Return the name of the given device or None if we don't know."""
        # If not initialised and not already scanned and not found.
        if device not in self.last_results:
            self._update_info()

            if not self.last_results:
                return None

        return self.last_results.get(device)

    def _update_info(self):
        """Ensure the information from the BT Home Hub 5 is up to date.

        Return boolean if scanning successful.
        """
        if not self.success_init:
            return False

        _LOGGER.info("Scanning")

        data = _get_homehub_data(self.url)

        if not data:
            _LOGGER.warning("Error scanning devices")
            return False

        self.last_results = data

        return True


def _get_homehub_data(url):
    """Retrieve data from BT Home Hub 5 and return parsed result."""
    try:
        response = requests.get(url, timeout=8)
    except requests.exceptions.Timeout:
        _LOGGER.exception("Connection to the router timed out")
        return
    if response.status_code == 200:
        return _parse_homehub_response(response.text)
    else:
        _LOGGER.error("Invalid response from Home Hub: %s", response)


def _parse_homehub_response(data_str):
    """Parse the BT Home Hub 5 data format."""
    from bs4 import BeautifulSoup

    # Find the beginning of devices table (the header)
    soup = BeautifulSoup(data_str, 'html.parser')
    macaddr_header = soup.find(text='MAC Address')
    if macaddr_header is None:
        _LOGGER.error("Could not find 'MAC Address' header")
        return
    table_header_row = macaddr_header.parent.parent # -> th -> tr
    if table_header_row.name != 'tr':
        _LOGGER.error("Header row not in the expected place")
        return

    # Identify columns of mac addr and device name. Device name is sadly
    # truncated, but the untuncated one requires authentication to get to.
    mac_address_col = None
    device_name_col = None
    for i, headercell in enumerate(table_header_row.children):
        if headercell.find(text='MAC Address'): mac_address_col = i
        elif headercell.find(text='Device'): device_name_col = i
    if device_name_col is None or mac_address_col is None:
        _LOGGER.error("Couldn't identify column nos of mac address and device name")
        return

    # Run through all the rows of the table, hunting for anything with a MAC
    devices = {}
    tablerow = table_header_row
    while tablerow.next_sibling is not None and 'bgcolor' in tablerow.next_sibling.attrs:
        tablerow = tablerow.next_sibling
        cells = list(tablerow.children)
        mac_address = cells[mac_address_col].text
        device_name = cells[device_name_col].text
        if _MAC_REGEX.match(mac_address):
            devices[mac_address] = device_name

    return devices
