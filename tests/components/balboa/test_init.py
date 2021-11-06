"""Tests of the initialization of the balboa integration."""

from unittest.mock import patch

from homeassistant.components.balboa.const import DOMAIN as BALBOA_DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant

from . import BalboaMock

from tests.common import MockConfigEntry

TEST_HOST = "balboatest.localdomain"
TEST_NAME = "FakeSpa"


async def test_setup_entry(hass: HomeAssistant):
    """Validate that setup entry also configure the client."""
    config_entry = MockConfigEntry(
        domain=BALBOA_DOMAIN,
        data={
            CONF_HOST: TEST_HOST,
            CONF_NAME: TEST_NAME,
        },
    )
    config_entry.add_to_hass(hass)

    with patch(
        "homeassistant.components.balboa.BalboaSpaWifi",
        new=BalboaMock,
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    assert config_entry.state == ConfigEntryState.LOADED

    await hass.config_entries.async_unload(config_entry.entry_id)

    assert config_entry.state == ConfigEntryState.NOT_LOADED


async def test_setup_entry_fails(hass):
    """Validate that setup entry also configure the client."""
    config_entry = MockConfigEntry(
        domain=BALBOA_DOMAIN,
        data={
            CONF_HOST: TEST_HOST,
            CONF_NAME: TEST_NAME,
        },
    )
    config_entry.add_to_hass(hass)

    with patch(
        "homeassistant.components.balboa.BalboaSpaWifi.connect",
        new=BalboaMock.broken_connect,
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    assert config_entry.state == ConfigEntryState.SETUP_RETRY
