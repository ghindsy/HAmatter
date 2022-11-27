"""Test the Min/Max integration."""
import pytest

from homeassistant.components.min_max.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component

from .test_sensor import VALUES

from tests.common import MockConfigEntry


@pytest.mark.parametrize("platform", ("sensor",))
async def test_setup_and_remove_config_entry(
    hass: HomeAssistant,
    platform: str,
) -> None:
    """Test setting up and removing a config entry."""
    hass.states.async_set("sensor.input_one", "10")
    hass.states.async_set("sensor.input_two", "20")

    input_sensors = ["sensor.input_one", "sensor.input_two"]

    registry = er.async_get(hass)
    min_max_entity_id = f"{platform}.my_min_max"

    # Setup the config entry
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            "entity_ids": input_sensors,
            "name": "My min_max",
            "round_digits": 2.0,
            "type": "max",
        },
        title="My min_max",
    )
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Check the entity is registered in the entity registry
    assert registry.async_get(min_max_entity_id) is not None

    # Check the platform is setup correctly
    state = hass.states.get(min_max_entity_id)
    assert state.state == "20.0"

    # Remove the config entry
    assert await hass.config_entries.async_remove(config_entry.entry_id)
    await hass.async_block_till_done()

    # Check the state and entity registry entry are removed
    assert hass.states.get(min_max_entity_id) is None
    assert registry.async_get(min_max_entity_id) is None


async def test_setup_config(hass: HomeAssistant) -> None:
    """Test setup from yaml."""
    config = {
        DOMAIN: [
            {
                "name": "My Min",
                "type": "min",
                "entity_ids": ["sensor.test_1", "sensor.test_2", "sensor.test_3"],
            },
            {
                "name": "My Max",
                "type": "max",
                "entity_ids": ["sensor.test_1", "sensor.test_2", "sensor.test_3"],
            },
        ]
    }

    assert await async_setup_component(hass, DOMAIN, config)
    await hass.async_block_till_done()

    entity_ids = config[DOMAIN][0]["entity_ids"]

    for entity_id, value in dict(zip(entity_ids, VALUES)).items():
        hass.states.async_set(entity_id, value)
        await hass.async_block_till_done()

    state1 = hass.states.get("sensor.my_min")
    state2 = hass.states.get("sensor.my_max")

    assert str(float(min(VALUES))) == state1.state
    assert str(float(max(VALUES))) == state2.state
