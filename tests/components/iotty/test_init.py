"""Tests for the Elgato Key Light integration."""
from unittest.mock import MagicMock

from homeassistant.components.iotty.const import DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow

from tests.common import MockConfigEntry


async def test_load_unload_config_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_iotty: MagicMock,
    local_impl,
) -> None:
    """Test the configuration entry loading/unloading."""

    mock_config_entry.add_to_hass(hass)
    assert mock_config_entry.data["auth_implementation"] is not None

    config_entry_oauth2_flow.async_register_implementation(hass, DOMAIN, local_impl)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED

    await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert not hass.data.get(DOMAIN)
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


# async def test_config_entry_not_ready(
#     hass: HomeAssistant,
#     mock_config_entry: MockConfigEntry,
#     mock_elgato: MagicMock,
# ) -> None:
#     """Test the Elgato configuration entry not ready."""
#     mock_elgato.state.side_effect = ElgatoConnectionError

#     mock_config_entry.add_to_hass(hass)
#     await hass.config_entries.async_setup(mock_config_entry.entry_id)
#     await hass.async_block_till_done()

#     assert len(mock_elgato.state.mock_calls) == 1
#     assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY
