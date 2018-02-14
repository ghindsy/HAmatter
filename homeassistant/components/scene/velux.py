"""
Support for VELUX scenes.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/scene.velux/
"""
import asyncio

from homeassistant.components.scene import Scene
from homeassistant.components.velux import _LOGGER, DATA_VELUX


DEPENDENCIES = ['velux']


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices,
                         discovery_info=None):
    """Set up the scenes for velux platform."""
    entities = []
    for scene in hass.data[DATA_VELUX].pyvlx.scenes:
        entities.append(VeluxScene(scene))
    async_add_devices(entities)
    return True


class VeluxScene(Scene):
    """Representation of a velux scene."""

    def __init__(self, scene):
        """Init velux scene."""
        _LOGGER.info("Adding VELUX scene: %s", scene)
        self.scene = scene

    @property
    def name(self):
        """Return the name of the scene."""
        return self.scene.name

    @asyncio.coroutine
    def async_activate(self):
        """Activate the scene."""
        yield from self.scene.run()
