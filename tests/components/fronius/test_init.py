"""Test the Fronius integration."""
from datetime import timedelta
from unittest.mock import patch

from pyfronius import FroniusError

from homeassistant.components.fronius.const import DOMAIN, SOLAR_NET_RESCAN_TIMER
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.util import dt as dt_util

from . import mock_responses, setup_fronius_integration

from tests.common import async_fire_time_changed
from tests.test_util.aiohttp import AiohttpClientMocker


async def test_unload_config_entry(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test that configuration entry supports unloading."""
    mock_responses(aioclient_mock)
    await setup_fronius_integration(hass)

    fronius_entries = hass.config_entries.async_entries(DOMAIN)
    assert len(fronius_entries) == 1

    test_entry = fronius_entries[0]
    assert test_entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(test_entry.entry_id)
    await hass.async_block_till_done()

    assert test_entry.state is ConfigEntryState.NOT_LOADED
    assert not hass.data.get(DOMAIN)


async def test_logger_error(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test setup when logger reports an error."""
    # gen24 dataset will raise FroniusError when logger is called
    mock_responses(aioclient_mock, fixture_set="gen24")
    config_entry = await setup_fronius_integration(hass, is_logger=True)
    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_inverter_error(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test setup when inverter_info reports an error."""
    mock_responses(aioclient_mock)
    with patch(
        "pyfronius.Fronius.inverter_info",
        side_effect=FroniusError,
    ):
        config_entry = await setup_fronius_integration(hass)
        assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_inverter_night_rescan(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test dynamic adding of an inverter discovered automatically after a Home Assistant reboot during the night."""
    mock_responses(aioclient_mock, fixture_set="igplus_v2", night=True)
    config_entry = await setup_fronius_integration(hass, is_logger=True)
    assert config_entry.state is ConfigEntryState.LOADED

    # Only expect logger during the night
    fronius_entries = hass.config_entries.async_entries(DOMAIN)
    assert len(fronius_entries) == 1

    # Switch to daytime
    mock_responses(aioclient_mock, fixture_set="igplus_v2", night=False)
    async_fire_time_changed(
        hass, dt_util.utcnow() + timedelta(minutes=SOLAR_NET_RESCAN_TIMER)
    )
    await hass.async_block_till_done()

    # We expect our inverter to be present now
    device_registry = dr.async_get(hass)
    inverter_1 = device_registry.async_get_device(identifiers={(DOMAIN, "203200")})
    assert inverter_1.manufacturer == "Fronius"

    # After another re-scan we still only expect this inverter
    async_fire_time_changed(
        hass, dt_util.utcnow() + timedelta(minutes=SOLAR_NET_RESCAN_TIMER * 2)
    )
    await hass.async_block_till_done()
    inverter_1 = device_registry.async_get_device(identifiers={(DOMAIN, "203200")})
    assert inverter_1.manufacturer == "Fronius"


async def test_inverter_rescan_interruption(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test test interruption of re-scan during runtime to only cause a warning."""
    mock_responses(aioclient_mock, fixture_set="igplus_v2", night=False)
    config_entry = await setup_fronius_integration(hass, is_logger=True)
    assert config_entry.state is ConfigEntryState.LOADED

    with patch(
        "pyfronius.Fronius.inverter_info",
        side_effect=FroniusError,
    ):
        async_fire_time_changed(
            hass, dt_util.utcnow() + timedelta(minutes=SOLAR_NET_RESCAN_TIMER)
        )
        await hass.async_block_till_done()
