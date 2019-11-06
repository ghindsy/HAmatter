"""Tests for the WLED integration."""

from homeassistant.components.wled.const import DOMAIN
from homeassistant.const import CONF_HOST, CONF_MAC
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry, load_fixture
from tests.test_util.aiohttp import AiohttpClientMocker


async def init_integration(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> MockConfigEntry:
    """Set up the WLED integration in Home Assistant."""
    aioclient_mock.get(
        "http://example.local:80/json/",
        text=load_fixture("wled.json"),
        headers={"Content-Type": "application/json"},
    )

    aioclient_mock.post(
        "http://example.local:80/json/state",
        json={"success": True},
        headers={"Content-Type": "application/json"},
    )

    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_HOST: "example.local", CONF_MAC: "aabbccddeeff"}
    )

    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)

    return entry
