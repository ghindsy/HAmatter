"""
homeassistant.components.light.rfxtrx
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Support for Rfxtrx lights.

Configuration:

To use Rfxtrx lights you will need to add the following to your
configuration.yaml file.

light:
  platform: rfxtrx

  devices:
    ac09c4f1: Bedroom Light
    ac09c4f2: Kitchen Light
    ac09c4f3: Bathroom Light

*Optional*

  # Automatic add new light
  automatic_add: True

"""
import logging
import homeassistant.components.rfxtrx as rfxtrx
from RFXtrx import LightingDevice

from homeassistant.components.light import Light
from homeassistant.util import slugify

REQUIREMENTS = ['https://github.com/Danielhiversen/pyRFXtrx/archive/' +
                'ec7a1aaddf8270db6e5da1c13d58c1547effd7cf.zip#RFXtrx==0.15']

DOMAIN = "rfxtrx"

def setup_platform(hass, config, add_devices_callback, discovery_info=None):
    """ Setup the RFXtrx platform. """
    logger = logging.getLogger(__name__)

    # Add light from config file
    lights = []
    devices = config.get('devices')
    for entity_id, entity_name in devices.items():
        if entity_id not in rfxtrx.RFX_DEVICES:
            logger.info("Add %s rfxtrx.light" % entity_name)
            new_light = RfxtrxLight(entity_name, False)
            rfxtrx.RFX_DEVICES[entity_id] = new_light
            lights.append(new_light)

    add_devices_callback(lights)

    def light_update(event):
        """ Callback for sensor updates from the RFXtrx gateway. """
        if isinstance(event.device, LightingDevice):
            entity_id = slugify(event.device.id_string.lower())

            # Add entity if not exist and the automatic_add is True
            if entity_id not in rfxtrx.RFX_DEVICES:
                automatic_add = config.get('automatic_add', False)
                if automatic_add:
                    logger.info("Automatic add %s rfxtrx.light" % entity_name)
                    new_light = RfxtrxLight(entity_id, False)
                    rfxtrx.RFX_DEVICES[entity_id] = new_light
                    add_devices_callback([new_light])

            # Check if entity exists (previous automatic added)
            if entity_id in rfxtrx.RFX_DEVICES:
                if event.values['Command'] == 'On' or event.values['Command'] == 'Off':
                    if event.values['Command'] == 'On':
                        rfxtrx.RFX_DEVICES[entity_id].turn_on()
                    else:
                        rfxtrx.RFX_DEVICES[entity_id].turn_off()

    if light_update not in rfxtrx.RECEIVED_EVT_SUBSCRIBERS:
        rfxtrx.RECEIVED_EVT_SUBSCRIBERS.append(light_update)


class RfxtrxLight(Light):
    """ Provides a demo switch. """
    def __init__(self, name, state):
        self._name = name
        self._state = state

    @property
    def should_poll(self):
        """ No polling needed for a demo light. """
        return False

    @property
    def name(self):
        """ Returns the name of the device if any. """
        return self._name

    @property
    def is_on(self):
        """ True if device is on. """
        return self._state

    def turn_on(self, **kwargs):
        """ Turn the device on. """
        self._state = True
        self.update_ha_state()

    def turn_off(self, **kwargs):
        """ Turn the device off. """
        self._state = False
        self.update_ha_state()