"""Support for Velux lights."""
from pyvlx import Intensity, LighteningDevice

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    SUPPORT_BRIGHTNESS,
    LightEntity,
)

from . import DATA_VELUX, VeluxEntity


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up light(s) for Velux platform."""
    entities = []
    for node in hass.data[DATA_VELUX].pyvlx.nodes:
        if isinstance(node, LighteningDevice):
            entities.append(VeluxLight(node))
    async_add_entities(entities)


class VeluxLight(VeluxEntity, LightEntity):
    """Representation of a Velux light."""

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_BRIGHTNESS

    @property
    def brightness(self):
        """Return the current brightness."""
        brightness = int((100 - self.node.intensity.intensity_percent) * 255 / 100)
        return brightness

    @property
    def is_on(self):
        """Return true if light is on."""
        return not self.node.intensity.off and self.node.intensity.known

    async def async_turn_on(self, **kwargs):
        """Instruct the light to turn on."""
        if ATTR_BRIGHTNESS in kwargs:
            intensity_percent = int(100 - kwargs[ATTR_BRIGHTNESS] / 255 * 100)
            await self.node.set_intensity(
                Intensity(intensity_percent=intensity_percent),
                wait_for_completion=False,
            )
        else:
            await self.node.turn_on(wait_for_completion=False)

    async def async_turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        await self.node.turn_off(wait_for_completion=False)
