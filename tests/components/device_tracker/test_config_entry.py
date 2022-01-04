"""Test Device Tracker config entry things."""
from homeassistant.components.device_tracker import config_entry as ce
from homeassistant.helpers import device_registry as dr, entity_registry as er

from tests.common import MockConfigEntry


def test_tracker_entity():
    """Test tracker entity."""

    class TestEntry(ce.TrackerEntity):
        """Mock tracker class."""

        should_poll = False

    instance = TestEntry()

    assert instance.force_update

    instance.should_poll = True

    assert not instance.force_update


async def test_register_mac(hass):
    """Test registering a mac."""
    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)

    config_entry = MockConfigEntry(domain="test")
    config_entry.add_to_hass(hass)

    mac1 = "12:34:56:AB:CD:EF"

    entity_entry_1 = ent_reg.async_get_or_create(
        "device_tracker",
        "test",
        mac1 + "yo1",
        original_name="name 1",
        config_entry=config_entry,
        disabled_by=er.RegistryEntryDisabler.INTEGRATION,
    )

    ce._async_register_mac(hass, "test", mac1, mac1 + "yo1")

    dev_reg.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, mac1)},
    )

    await hass.async_block_till_done()

    entity_entry_1 = ent_reg.async_get(entity_entry_1.entity_id)

    assert entity_entry_1.disabled_by is None
