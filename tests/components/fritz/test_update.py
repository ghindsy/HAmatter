"""The tests for the Fritzbox update entity."""

from unittest.mock import patch

from aiohttp import ClientSession

from homeassistant.components.fritz.const import DOMAIN
from homeassistant.components.update import DOMAIN as UPDATE_DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from .const import MOCK_FIRMWARE, MOCK_FIRMWARE_AVAILABLE, MOCK_USER_DATA

from tests.common import MockConfigEntry


async def test_update_entities_initialized(
    hass: HomeAssistant, hass_client: ClientSession, fc_class_mock, fh_class_mock
):
    """Test update entities."""

    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_USER_DATA)
    entry.add_to_hass(hass)

    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    assert entry.state == ConfigEntryState.LOADED

    updates = hass.states.async_all(UPDATE_DOMAIN)
    assert len(updates) == 1


async def test_update_available(
    hass: HomeAssistant, hass_client: ClientSession, fc_class_mock, fh_class_mock
):
    """Test update entities."""

    with patch(
        "homeassistant.components.fritz.common.FritzBoxTools._update_device_info",
        return_value=(True, MOCK_FIRMWARE_AVAILABLE),
    ):
        entry = MockConfigEntry(domain=DOMAIN, data=MOCK_USER_DATA)
        entry.add_to_hass(hass)

        assert await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()
        assert entry.state == ConfigEntryState.LOADED

        update = hass.states.get("update.update.mock_title_fritz_os")
        assert update is not None
        assert update.state == "on"
        assert update.attributes.get("installed_version") == MOCK_FIRMWARE
        assert update.attributes.get("latest_version") == MOCK_FIRMWARE_AVAILABLE


async def test_no_update_available(
    hass: HomeAssistant, hass_client: ClientSession, fc_class_mock, fh_class_mock
):
    """Test update entities."""

    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_USER_DATA)
    entry.add_to_hass(hass)

    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    assert entry.state == ConfigEntryState.LOADED

    update = hass.states.get("update.mock_title_fritz_os")
    assert update is not None
    assert update.state == "off"
    assert update.attributes.get("installed_version") == MOCK_FIRMWARE
    assert update.attributes.get("latest_version") == MOCK_FIRMWARE
