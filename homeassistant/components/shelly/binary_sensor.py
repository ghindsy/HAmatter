"""Binary sensor for Shelly."""
from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_CONNECTIVITY,
    DEVICE_CLASS_GAS,
    DEVICE_CLASS_MOISTURE,
    DEVICE_CLASS_OPENING,
    DEVICE_CLASS_PROBLEM,
    DEVICE_CLASS_SAFETY,
    DEVICE_CLASS_SMOKE,
    DEVICE_CLASS_VIBRATION,
    BinarySensorEntity,
)

from .entity import (
    BlockAttributeDescription,
    RestAttributeDescription,
    ShellyBlockAttributeEntity,
    ShellyRestAttributeEntity,
    async_setup_entry_attribute_entities,
    async_setup_entry_rest,
)

SENSORS = {
    ("device", "overtemp"): BlockAttributeDescription(
        name="Overheating", device_class=DEVICE_CLASS_PROBLEM
    ),
    ("device", "overpower"): BlockAttributeDescription(
        name="Overpowering", device_class=DEVICE_CLASS_PROBLEM
    ),
    ("light", "overpower"): BlockAttributeDescription(
        name="Overpowering", device_class=DEVICE_CLASS_PROBLEM
    ),
    ("relay", "overpower"): BlockAttributeDescription(
        name="Overpowering", device_class=DEVICE_CLASS_PROBLEM
    ),
    ("sensor", "dwIsOpened"): BlockAttributeDescription(
        name="Door", device_class=DEVICE_CLASS_OPENING
    ),
    ("sensor", "flood"): BlockAttributeDescription(
        name="Flood", device_class=DEVICE_CLASS_MOISTURE
    ),
    ("sensor", "gas"): BlockAttributeDescription(
        name="Gas",
        device_class=DEVICE_CLASS_GAS,
        value=lambda value: value in ["mild", "heavy"],
        device_state_attributes=lambda block: {"detected": block.gas},
    ),
    ("sensor", "smoke"): BlockAttributeDescription(
        name="Smoke", device_class=DEVICE_CLASS_SMOKE
    ),
    ("sensor", "vibration"): BlockAttributeDescription(
        name="Vibration", device_class=DEVICE_CLASS_VIBRATION
    ),
}

REST_SENSORS = {
    ("cloud"): RestAttributeDescription(
        name="Cloud",
        device_class=DEVICE_CLASS_CONNECTIVITY,
        path="cloud/connected",
    ),
    ("fwupdate"): RestAttributeDescription(
        name="Firmware update (release)",
        device_class=DEVICE_CLASS_SAFETY,
        path="update/has_update",
        attributes={"description": "Available version:", "path": "update/new_version"},
    ),
}


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up sensors for device."""
    await async_setup_entry_attribute_entities(
        hass, config_entry, async_add_entities, SENSORS, ShellyBinarySensor
    )

    await async_setup_entry_rest(
        hass, config_entry, async_add_entities, REST_SENSORS, ShellyRestBinarySensor
    )


class ShellyBinarySensor(ShellyBlockAttributeEntity, BinarySensorEntity):
    """Shelly binary sensor entity."""

    @property
    def is_on(self):
        """Return true if sensor state is on."""
        return bool(self.attribute_value)


class ShellyRestBinarySensor(ShellyRestAttributeEntity, BinarySensorEntity):
    """Shelly REST binary sensor entity."""

    @property
    def is_on(self):
        """Return true if REST sensor state is on."""
        return bool(self.attribute_value)
