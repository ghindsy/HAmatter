"""Tests for emulated_roku config flow."""
from spencerassistant import config_entries
from spencerassistant.components.emulated_roku import config_flow

from tests.common import MockConfigEntry


async def test_flow_works(hass, mock_get_source_ip):
    """Test that config flow works."""
    result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={"name": "Emulated Roku Test", "listen_port": 8060},
    )

    assert result["type"] == "create_entry"
    assert result["title"] == "Emulated Roku Test"
    assert result["data"] == {"name": "Emulated Roku Test", "listen_port": 8060}


async def test_flow_already_registered_entry(hass, mock_get_source_ip):
    """Test that config flow doesn't allow existing names."""
    MockConfigEntry(
        domain="emulated_roku", data={"name": "Emulated Roku Test", "listen_port": 8062}
    ).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={"name": "Emulated Roku Test", "listen_port": 8062},
    )

    assert result["type"] == "abort"
    assert result["reason"] == "already_configured"
