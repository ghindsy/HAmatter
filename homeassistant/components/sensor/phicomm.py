"""
Support for Phicomm air sensor.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.phicomm/
"""

import asyncio
import logging

from datetime import timedelta

import requests
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_NAME, CONF_USERNAME, CONF_PASSWORD,
    CONF_SENSORS, CONF_SCAN_INTERVAL, TEMP_CELSIUS)
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_time_interval
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

AUTH_CODE = 'feixun.SH_1'
TOKEN_FILE = '.phicomm.token.'
USER_AGENT = 'zhilian/5.7.0 (iPhone; iOS 10.0.2; Scale/3.00)'

TOKEN_URL = 'https://accountsym.phicomm.com/v1/login'
DATA_URL = 'https://aircleaner.phicomm.com/aircleaner/getIndexData'

SENSOR_PM25 = 'pm25'
SENSOR_HCHO = 'hcho'
SENSOR_TEMPERATURE = 'temperature'
SENSOR_HUMIDITY = 'humidity'

DEFAULT_NAME = 'Phicomm'
DEFAULT_SENSORS = [SENSOR_PM25, SENSOR_HCHO,
                   SENSOR_TEMPERATURE, SENSOR_HUMIDITY]

SENSOR_MAP = {
    SENSOR_PM25: ('PM2.5', 'μg/m³', 'blur'),
    SENSOR_HCHO: ('HCHO', 'mg/m³', 'biohazard'),
    SENSOR_TEMPERATURE: ('Temperature', TEMP_CELSIUS, 'thermometer'),
    SENSOR_HUMIDITY: ('Humidity', '%', 'water-percent')
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_SENSORS, default=DEFAULT_SENSORS):
        vol.All(cv.ensure_list, vol.Length(min=1), [vol.In(SENSOR_MAP)]),
    vol.Optional(CONF_SCAN_INTERVAL, default=timedelta(seconds=120)): (
        vol.All(cv.time_period, cv.positive_timedelta)),
})


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up the Phicomm sensor."""
    name = config.get(CONF_NAME)
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)
    sensors = config.get(CONF_SENSORS)
    scan_interval = config.get(CONF_SCAN_INTERVAL)

    phicomm = PhicommData(hass, username, password)
    devices = yield from phicomm.make_sensors(name, sensors)
    if devices:
        async_add_devices(devices)
        async_track_time_interval(hass, phicomm.async_update, scan_interval)
    else:
        _LOGGER.error("No sensors added: %s.", name)


class PhicommSensor(Entity):
    """Implementation of a Phicomm sensor."""

    def __init__(self, phicomm, name, index, sensor_type):
        """Initialize the Phicomm sensor."""
        sensor_name, unit, icon = SENSOR_MAP[sensor_type]
        if index:
            name += str(index + 1)
        self._name = name + ' ' + sensor_name
        self._index = index
        self._sensor_type = sensor_type
        self._unit = unit
        self._icon = 'mdi:' + icon
        self.phicomm = phicomm

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return self._icon

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._unit

    @property
    def available(self):
        """Return if the sensor data are available."""
        data = self.data
        return data and data.get('online') == '1'

    @property
    def state(self):
        """Return the state of the device."""
        return self.state_from_devs(self.phicomm.devs)

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self.data if self._sensor_type == SENSOR_PM25 else None

    @property
    def should_poll(self):  # pylint: disable=no-self-use
        """No polling needed."""
        return False

    @property
    def data(self):
        """Get data with current device index."""
        devs = self.phicomm.devs
        if devs and self._index < len(devs):
            return devs[self._index].get('catDev')
        return None

    def state_from_devs(self, devs):
        """Get state from Phicomm devs."""
        if devs and self._index < len(devs):
            return devs[self._index].get('catDev').get(self._sensor_type)
        return None


class PhicommData():
    """Class for handling the data retrieval."""

    def __init__(self, hass, username, password):
        """Initialize the data object."""
        self._hass = hass
        self._username = username
        self._password = password
        self._token_path = hass.config.path(TOKEN_FILE + username)
        self._token = None
        self._devices = None
        self.devs = None

    @asyncio.coroutine
    def make_sensors(self, name, sensors):
        """Make sensors with online data."""
        try:
            with open(self._token_path) as file:
                self._token = file.read()
                _LOGGER.debug("Load: %s => %s", self._token_path, self._token)
        except BaseException:
            pass

        self.update_data()
        if not self.devs:
            return None

        devices = []
        for index in range(len(self.devs)):
            for sensor_type in sensors:
                devices.append(PhicommSensor(self, name, index, sensor_type))
        self._devices = devices
        return devices

    @asyncio.coroutine
    def async_update(self, time):
        """Update online data and update ha state."""
        old_devs = self.devs
        self.update_data()

        tasks = []
        for device in self._devices:
            if device.state != device.state_from_devs(old_devs):
                _LOGGER.info('%s: => %s', device.name, device.state)
                tasks.append(device.async_update_ha_state())

        if tasks:
            yield from asyncio.wait(tasks, loop=self._hass.loop)

    def update_data(self):
        """Update online data."""
        try:
            json = self.fetch_data()
            if ('error' in json) and (json['error'] != '0'):
                _LOGGER.debug("Reset token: error=%s", json['error'])
                self._token = None
                json = self.fetch_data()
            self.devs = json['data']['devs']
            _LOGGER.info("Get data: devs=%s", self.devs)
        except BaseException:
            import traceback
            _LOGGER.error('Exception: %s', traceback.format_exc())

    def fetch_data(self):
        """Fetch the latest data from Phicomm server."""
        if self._token is None:
            import hashlib
            md5 = hashlib.md5()
            md5.update(self._password.encode('utf8'))
            data = {
                'authorizationcode': AUTH_CODE,
                'phonenumber': self._username,
                'password': md5.hexdigest().upper()
            }
            headers = {'User-Agent': USER_AGENT}
            json = requests.post(TOKEN_URL, headers=headers, data=data).json()
            _LOGGER.debug("Get token: %s", json)
            if 'access_token' in json:
                self._token = json['access_token']
                with open(self._token_path, 'w') as file:
                    file.write(self._token)
            else:
                return None
        headers = {'User-Agent': USER_AGENT, 'Authorization': self._token}
        return requests.get(DATA_URL, headers=headers).json()
