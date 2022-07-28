"""Test the Anthem A/V Receivers config flow."""
from unittest.mock import ANY, AsyncMock, patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry


async def test_load_unload_config_entry(
    hass: HomeAssistant,
    mock_connection_create: AsyncMock,
    mock_anthemav: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test load and unload AnthemAv component."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # assert avr is created
    mock_connection_create.assert_called_with(
        host="1.1.1.1", port=14999, update_callback=ANY
    )
    assert mock_config_entry.state == config_entries.ConfigEntryState.LOADED

    # unload
    await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    # assert unload and avr is closed
    assert mock_config_entry.state == config_entries.ConfigEntryState.NOT_LOADED
    mock_anthemav.close.assert_called_once()


async def test_config_entry_not_ready(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test AnthemAV configuration entry not ready."""

    with patch(
        "anthemav.Connection.create",
        side_effect=OSError,
    ):
        mock_config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        assert mock_config_entry.state is config_entries.ConfigEntryState.SETUP_RETRY
