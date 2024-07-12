"""Tests for Motionblinds BLE init."""

from unittest.mock import patch

from homeassistant.components.motionblinds_ble import PLATFORMS, options_update_listener
from homeassistant.core import HomeAssistant

from . import SERVICE_INFO, setup_platform

from tests.components.bluetooth import inject_bluetooth_service_info


async def test_options_update_listener(hass: HomeAssistant) -> None:
    """Test options_update_listener."""

    config_entry, _ = await setup_platform(hass, PLATFORMS)

    with (
        patch(
            "homeassistant.components.motionblinds_ble.MotionDevice.set_custom_disconnect_time"
        ) as mock_set_custom_disconnect_time,
        patch(
            "homeassistant.components.motionblinds_ble.MotionDevice.set_permanent_connection"
        ) as set_permanent_connection,
    ):
        await options_update_listener(hass, config_entry)
        mock_set_custom_disconnect_time.assert_called_once()
        set_permanent_connection.assert_called_once()


async def test_update_ble_device(hass: HomeAssistant) -> None:
    """Test async_update_ble_device."""

    await setup_platform(hass, PLATFORMS)

    with patch(
        "homeassistant.components.motionblinds_ble.MotionDevice.set_ble_device"
    ) as mock_set_ble_device:
        inject_bluetooth_service_info(hass, SERVICE_INFO)
        mock_set_ble_device.assert_called_once()
