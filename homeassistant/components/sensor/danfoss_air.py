"""
Sensors for Danfoss Air HRV.

Configuration:
    danfoss_air:
        host: IP_OF_CCM_MODULE

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/sensor.danfoss_air/
"""
from homeassistant.const import TEMP_CELSIUS
from homeassistant.helpers.entity import Entity

SENSORS = {
        'exhaust': ["Danfoss Air Exhaust Temperature", TEMP_CELSIUS,
                    'EXHAUST_TEMPERATURE'],
        'outdoor': ["Danfoss Air Outdoor Temperature", TEMP_CELSIUS,
                    'OUTDOOR_TEMPERATURE'],
        'supply': ["Danfoss Air Supply Temperature", TEMP_CELSIUS,
                   'SUPPLY_TEMPERATURE'],
        'extract': ["Danfoss Air Extract Temperature", TEMP_CELSIUS,
                    'EXTRACT_TEMPERATURE'],
        'filterPercent': ["Danfoss Air Remaining Filter", '%',
                          'FILTER_PERCENT'],
        'humidityPercent': ["Danfoss Air Humidity", '%',
                            'HUMIDITY_PERCENT']
        }


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the available Danfoss Air sensors etc."""
    data = hass.data["DANFOSS_DO"]

    dev = []

    for key in SENSORS.keys():
        dev.append(DanfossAir(data, SENSORS[key][0], SENSORS[key][1],
                              SENSORS[key][2]))

    add_devices(dev, True)


class DanfossAir(Entity):
    """Representation of a Sensor."""

    def __init__(self, data, name, sensorUnit, sensorType):
        """Initialize the sensor."""
        self._data = data
        self._name = name
        self._state = None
        self._type = sensorType
        self._unit = sensorUnit

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit

    def update(self):
        """Update the new state of the sensor.

        This is done through the DanfossAir object tthat does the actually
        communication with the Air CCM.
        """
        self._data.update()

        self._state = self._data.getValue(self._type)
