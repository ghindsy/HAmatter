"""
homeassistant.components.sensor.yr
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Yr.no weather service.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.yr/
"""
import logging

from datetime import timedelta
import requests

from homeassistant.const import (ATTR_ENTITY_PICTURE,
                                 CONF_LATITUDE,
                                 CONF_LONGITUDE)
from homeassistant.helpers.entity import Entity
from homeassistant.util import location, dt as dt_util

_LOGGER = logging.getLogger(__name__)


REQUIREMENTS = ['xmltodict']

# Sensor types are defined like so:
SENSOR_TYPES = {
    'symbol': ['Symbol', None],
    'precipitation': ['Condition', 'mm'],
    'temperature': ['Temperature', '°C'],
    'windSpeed': ['Wind speed', 'm/s'],
    'windGust': ['Wind gust', 'm/s'],
    'pressure': ['Pressure', 'mbar'],
    'windDirection': ['Wind direction', '°'],
    'humidity': ['Humidity', '%'],
    'fog': ['Fog', '%'],
    'cloudiness': ['Cloudiness', '%'],
    'lowClouds': ['Low clouds', '%'],
    'mediumClouds': ['Medium clouds', '%'],
    'highClouds': ['High clouds', '%'],
    'dewpointTemperature': ['Dewpoint temperature', '°C'],
}


def setup_platform(hass, config, add_devices, discovery_info=None):
    """ Get the Yr.no sensor. """

    latitude = config.get(CONF_LATITUDE, hass.config.latitude)
    longitude = config.get(CONF_LONGITUDE, hass.config.longitude)
    elevation = config.get('elevation')
    forecast = config.get('forecast', {})

    if None in (latitude, longitude):
        _LOGGER.error("Latitude or longitude not set in Home Assistant config")
        return False

    if elevation is None:
        elevation = location.elevation(latitude,
                                       longitude)

    coordinates = dict(lat=latitude,
                       lon=longitude,
                       msl=elevation)

    weather = YrData(coordinates)

    dev = []
    if 'monitored_conditions' in config:
        for variable in config['monitored_conditions']:
            if variable not in SENSOR_TYPES:
                _LOGGER.error('Sensor type: "%s" does not exist', variable)
            else:
                dev.append(YrSensor(variable, weather, forecast))

    # add symbol as default sensor
    if len(dev) == 0:
        dev.append(YrSensor("symbol", weather, forecast))
    add_devices(dev)


# pylint: disable=too-many-instance-attributes
class YrSensor(Entity):
    """ Implements an Yr.no sensor. """

    def __init__(self, sensor_type, weather, forecast):
        self.client_name = 'yr'
        self._name = SENSOR_TYPES[sensor_type][0]
        self.type = sensor_type
        self._state = None
        self._weather = weather
        self._forecast = forecast
        self._unit_of_measurement = SENSOR_TYPES[self.type][1]
        self._update = None

        self.update()

    @property
    def name(self):
        return '{} {}'.format(self.client_name, self._name)

    @property
    def state(self):
        """ Returns the state of the device. """
        return self._state

    @property
    def state_attributes(self):
        """ Returns state attributes. """
        data = {
            'about': "Weather forecast from yr.no, delivered by the"
                     " Norwegian Meteorological Institute and the NRK"
        }
        if self.type == 'symbol':
            symbol_nr = self._state
            data[ATTR_ENTITY_PICTURE] = \
                "http://api.met.no/weatherapi/weathericon/1.1/" \
                "?symbol={0};content_type=image/png".format(symbol_nr)

        return data

    @property
    def unit_of_measurement(self):
        """ Unit of measurement of this entity, if any. """
        return self._unit_of_measurement

    def update(self):
        """ Gets the latest data from yr.no and updates the states. """

        now = dt_util.utcnow()
        # check if data should be updated
        if self._update is not None and now <= self._update:
            return

        if 'in' in self._forecast:
            now += timedelta(hours=self._forecast['in'])

        if 'at' in self._forecast:
            now = dt_util.as_local(now)
            now = now.replace(hour=self._forecast['at'],
                              minute=0,
                              second=0,
                              microsecond=0)
            now = dt_util.as_utc(now)

        self._weather.update()

        # find sensor
        for time_entry in self._weather.data['product']['time']:
            valid_from = dt_util.str_to_datetime(
                time_entry['@from'], "%Y-%m-%dT%H:%M:%SZ")
            valid_to = dt_util.str_to_datetime(
                time_entry['@to'], "%Y-%m-%dT%H:%M:%SZ")

            loc_data = time_entry['location']

            if self.type not in loc_data or now >= valid_to:
                continue

            self._update = valid_to

            if self.type == 'precipitation' and valid_from < now:
                self._state = loc_data[self.type]['@value']
                break
            elif self.type == 'symbol' and valid_from < now:
                self._state = loc_data[self.type]['@number']
                break
            elif self.type in ('temperature', 'pressure', 'humidity',
                               'dewpointTemperature'):
                self._state = loc_data[self.type]['@value']
                break
            elif self.type in ('windSpeed', 'windGust'):
                self._state = loc_data[self.type]['@mps']
                break
            elif self.type == 'windDirection':
                self._state = float(loc_data[self.type]['@deg'])
                break
            elif self.type in ('fog', 'cloudiness', 'lowClouds',
                               'mediumClouds', 'highClouds'):
                self._state = loc_data[self.type]['@percent']
                break


# pylint: disable=too-few-public-methods
class YrData(object):
    """ Gets the latest data and updates the states. """

    def __init__(self, coordinates):
        self._url = 'http://api.yr.no/weatherapi/locationforecast/1.9/?' \
            'lat={lat};lon={lon};msl={msl}'.format(**coordinates)

        self._nextrun = None
        self.data = {}
        self.update()

    def update(self):
        """ Gets the latest data from yr.no """
        # check if new will be available
        if self._nextrun is not None and dt_util.utcnow() <= self._nextrun:
            return
        try:
            with requests.Session() as sess:
                response = sess.get(self._url)
        except requests.RequestException:
            return
        if response.status_code != 200:
            return
        data = response.text

        import xmltodict
        self.data = xmltodict.parse(data)['weatherdata']
        model = self.data['meta']['model']
        if '@nextrun' not in model:
            model = model[0]
        self._nextrun = dt_util.str_to_datetime(model['@nextrun'],
                                                "%Y-%m-%dT%H:%M:%SZ")
