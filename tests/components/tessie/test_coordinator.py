"""Test the Tessie sensor platform."""
from unittest.mock import patch

from homeassistant.components.tessie.const import DOMAIN, TessieStatus
from homeassistant.core import HomeAssistant

from .common import (
    ERROR_AUTH,
    ERROR_CONNECTION,
    ERROR_TIMEOUT,
    ERROR_UNKNOWN,
    TEST_VEHICLE_STATE_ASLEEP,
    TEST_VEHICLE_STATE_ONLINE,
    setup_platform,
)


async def test_coordinator(hass: HomeAssistant) -> None:
    """Tests that the sensors are correct."""

    entry = await setup_platform(hass)
    coordinator = hass.data[DOMAIN][entry.entry_id][0]

    with patch(
        "homeassistant.components.tessie.coordinator.get_state",
        return_value=TEST_VEHICLE_STATE_ONLINE,
    ) as mock_get_state:
        await coordinator.async_refresh()
        assert coordinator.last_update_success is True
        assert coordinator.data["state"] == TessieStatus.ONLINE
        mock_get_state.assert_called_once()

    with patch(
        "homeassistant.components.tessie.coordinator.get_state",
        return_value=TEST_VEHICLE_STATE_ASLEEP,
    ) as mock_get_state:
        await coordinator.async_refresh()
        assert coordinator.last_update_success is True
        assert coordinator.data["state"] == TessieStatus.ASLEEP
        mock_get_state.assert_called_once()

    with patch(
        "homeassistant.components.tessie.coordinator.get_state",
        side_effect=ERROR_AUTH,
    ) as mock_get_state:
        await coordinator.async_refresh()
        assert coordinator.last_update_success is False
        mock_get_state.assert_called_once()

    with patch(
        "homeassistant.components.tessie.coordinator.get_state",
        side_effect=ERROR_TIMEOUT,
    ) as mock_get_state:
        await coordinator.async_refresh()
        assert coordinator.last_update_success is True
        assert coordinator.data["state"] == TessieStatus.OFFLINE
        mock_get_state.assert_called_once()

    with patch(
        "homeassistant.components.tessie.coordinator.get_state",
        side_effect=ERROR_UNKNOWN,
    ) as mock_get_state:
        await coordinator.async_refresh()
        assert coordinator.last_update_success is False
        mock_get_state.assert_called_once()

    with patch(
        "homeassistant.components.tessie.coordinator.get_state",
        side_effect=ERROR_CONNECTION,
    ) as mock_get_state:
        await coordinator.async_refresh()
        assert coordinator.last_update_success is False
        mock_get_state.assert_called_once()
