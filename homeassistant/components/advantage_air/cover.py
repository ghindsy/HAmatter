"""Cover platform for Advantage Air integration."""

from homeassistant.components.cover import (
    ATTR_POSITION,
    DEVICE_CLASS_DAMPER,
    SUPPORT_CLOSE,
    SUPPORT_OPEN,
    SUPPORT_SET_POSITION,
    CoverEntity,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ADVANTAGE_AIR_STATE_CLOSE, ADVANTAGE_AIR_STATE_OPEN, DOMAIN


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up AdvantageAir cover platform."""

    instance = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for ac_key, ac_device in instance["coordinator"].data["aircons"].items():
        for zone_key, zone in ac_device["zones"].items():
            # Only add zone vent controls when zone in vent control mode.
            if zone["type"] == 0:
                entities.append(AdvantageAirZoneVent(instance, ac_key, zone_key))
    async_add_entities(entities)


class AdvantageAirZoneVent(CoordinatorEntity, CoverEntity):
    """Advantage Air Cover Class."""

    def __init__(self, instance, ac_key, zone_key):
        """Initialize the Advantage Air Zone Vent cover entity."""
        super().__init__(instance["coordinator"])
        self.async_change = instance["async_change"]
        self.ac_key = ac_key
        self.zone_key = zone_key

    @property
    def _zone(self):
        return self.coordinator.data["aircons"][self.ac_key]["zones"][self.zone_key]

    @property
    def name(self):
        """Return the name."""
        return f'{self._zone["name"]}'

    @property
    def unique_id(self):
        """Return a unique id."""
        return f'{self.coordinator.data["system"]["rid"]}-{self.ac_key}-{self.zone_key}'

    @property
    def device_class(self):
        """Return the device class of the vent."""
        return DEVICE_CLASS_DAMPER

    @property
    def supported_features(self):
        """Return the supported features."""
        return SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_SET_POSITION

    @property
    def is_closed(self):
        """Return if vent is fully closed."""
        return self._zone["state"] == ADVANTAGE_AIR_STATE_CLOSE

    @property
    def current_cover_position(self):
        """Return vents current position as a percentage."""
        if self._zone["state"] == ADVANTAGE_AIR_STATE_OPEN:
            return self._zone["value"]
        return 0

    @property
    def icon(self):
        """Return vent icon."""
        if self._zone["state"] == ADVANTAGE_AIR_STATE_OPEN:
            return "mdi:fan"
        return "mdi:fan-off"

    @property
    def device_info(self):
        """Return parent device information."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.data["system"]["rid"])},
            "name": self.coordinator.data["system"]["name"],
            "manufacturer": "Advantage Air",
            "model": self.coordinator.data["system"]["sysType"],
            "sw_version": self.coordinator.data["system"]["myAppRev"],
        }

    async def async_open_cover(self, **kwargs):
        """Fully open zone vent."""
        await self.async_change(
            {
                self.ac_key: {
                    "zones": {
                        self.zone_key: {"state": ADVANTAGE_AIR_STATE_OPEN, "value": 100}
                    }
                }
            }
        )

    async def async_close_cover(self, **kwargs):
        """Fully close zone vent."""
        await self.async_change(
            {
                self.ac_key: {
                    "zones": {self.zone_key: {"state": ADVANTAGE_AIR_STATE_CLOSE}}
                }
            }
        )

    async def async_set_cover_position(self, **kwargs):
        """Change vent position."""
        position = round(kwargs.get(ATTR_POSITION) / 5) * 5
        if position == 0:
            await self.async_change(
                {
                    self.ac_key: {
                        "zones": {self.zone_key: {"state": ADVANTAGE_AIR_STATE_CLOSE}}
                    }
                }
            )
        else:
            await self.async_change(
                {
                    self.ac_key: {
                        "zones": {
                            self.zone_key: {
                                "state": ADVANTAGE_AIR_STATE_OPEN,
                                "value": position,
                            }
                        }
                    }
                }
            )
