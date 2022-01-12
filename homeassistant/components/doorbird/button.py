"""Support for powering relays in a DoorBird video doorbell."""

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DOOR_STATION, DOOR_STATION_INFO
from .entity import DoorBirdEntity

IR_RELAY = "__ir_light__"

RELAY_ENTITY_DESCRIPTION = ButtonEntityDescription(icon="mdi:dip-switch")
IR_ENTITY_DESCRIPTION = ButtonEntityDescription(icon="mdi:lightbulb")


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the DoorBird button platform."""
    config_entry_id = config_entry.entry_id

    data = hass.data[DOMAIN][config_entry_id]
    doorstation = data[DOOR_STATION]
    doorstation_info = data[DOOR_STATION_INFO]

    relays = doorstation_info["RELAYS"]
    relays.append(IR_RELAY)

    entities = [
        DoorBirdButton(doorstation, doorstation_info, relay) for relay in relays
    ]

    async_add_entities(entities)


class DoorBirdButton(DoorBirdEntity, ButtonEntity):
    """A relay in a DoorBird device."""

    def __init__(self, doorstation, doorstation_info, relay):
        """Initialize a relay in a DoorBird device."""
        super().__init__(doorstation, doorstation_info)
        self._doorstation = doorstation
        self._relay = relay
        if self._relay == IR_RELAY:
            self._attr_name = f"{self._doorstation.name} IR"
            self.entity_description = IR_ENTITY_DESCRIPTION
        else:
            self._attr_name = f"{self._doorstation.name} Relay {self._relay}"
            self.entity_description = RELAY_ENTITY_DESCRIPTION

        self._attr_unique_id = f"{self._mac_addr}_{self._relay}"

    def press(self):
        """Power the relay."""
        if self._relay == IR_RELAY:
            self._doorstation.device.turn_light_on()
        else:
            self._doorstation.device.energize_relay(self._relay)
