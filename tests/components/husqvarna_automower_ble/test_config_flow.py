"""Test the Husqvarna Bluetooth config flow."""

from unittest.mock import Mock

from bleak import BleakError
import pytest
from syrupy.assertion import SnapshotAssertion

from homeassistant import config_entries
from homeassistant.components.husqvarna_automower_ble.const import DOMAIN
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant

from . import (
    AUTOMOWER_MISSING_SERVICE_SERVICE_INFO,
    AUTOMOWER_SERVICE_INFO,
    AUTOMOWER_UNNAMED_SERVICE_INFO,
    AUTOMOWER_UNSUPPORTED_GROUP_SERVICE_INFO,
)

from tests.components.bluetooth import inject_bluetooth_service_info

pytestmark = pytest.mark.usefixtures("mock_setup_entry")


async def test_user_selection(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
) -> None:
    """Test we can select a device."""

    inject_bluetooth_service_info(hass, AUTOMOWER_SERVICE_INFO)
    inject_bluetooth_service_info(hass, AUTOMOWER_UNNAMED_SERVICE_INFO)
    await hass.async_block_till_done(wait_background_tasks=True)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result == snapshot

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"address": "00000000-0000-0000-0000-000000000001"},
    )
    assert result == snapshot

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={},
    )


async def test_no_devices(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
) -> None:
    """Test missing device."""

    inject_bluetooth_service_info(hass, AUTOMOWER_MISSING_SERVICE_SERVICE_INFO)
    inject_bluetooth_service_info(hass, AUTOMOWER_UNSUPPORTED_GROUP_SERVICE_INFO)
    await hass.async_block_till_done(wait_background_tasks=True)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result == snapshot


async def test_bluetooth(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
) -> None:
    """Test bluetooth device discovery."""

    inject_bluetooth_service_info(hass, AUTOMOWER_SERVICE_INFO)
    await hass.async_block_till_done(wait_background_tasks=True)

    result = hass.config_entries.flow.async_progress_by_handler(DOMAIN)[0]
    assert result == snapshot

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={},
    )


async def test_bluetooth_invalid(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
) -> None:
    """Test bluetooth device discovery with invalid data."""

    inject_bluetooth_service_info(hass, AUTOMOWER_UNSUPPORTED_GROUP_SERVICE_INFO)
    await hass.async_block_till_done(wait_background_tasks=True)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=AUTOMOWER_UNSUPPORTED_GROUP_SERVICE_INFO,
    )
    assert result == snapshot


async def test_failed_connect(
    hass: HomeAssistant,
    mock_client: Mock,
    snapshot: SnapshotAssertion,
) -> None:
    """Test we can select a device."""

    inject_bluetooth_service_info(hass, AUTOMOWER_SERVICE_INFO)
    inject_bluetooth_service_info(hass, AUTOMOWER_UNNAMED_SERVICE_INFO)
    await hass.async_block_till_done(wait_background_tasks=True)

    mock_client.connect.side_effect = False

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result == snapshot

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"address": "00000000-0000-0000-0000-000000000001"},
    )
    assert result == snapshot

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={},
    )


async def test_exception_connect(
    hass: HomeAssistant,
    mock_client: Mock,
    snapshot: SnapshotAssertion,
) -> None:
    """Test we can select a device."""

    inject_bluetooth_service_info(hass, AUTOMOWER_SERVICE_INFO)
    inject_bluetooth_service_info(hass, AUTOMOWER_UNNAMED_SERVICE_INFO)
    await hass.async_block_till_done(wait_background_tasks=True)

    async def _probe_gatts(self, device):
        """Mock BleakClient.probe_gatts."""
        raise BleakError

    mock_client.probe_gatts = _probe_gatts


async def test_failed_is_connected(
    hass: HomeAssistant,
    mock_client: Mock,
    snapshot: SnapshotAssertion,
) -> None:
    """Test we can select a device."""

    inject_bluetooth_service_info(hass, AUTOMOWER_SERVICE_INFO)
    inject_bluetooth_service_info(hass, AUTOMOWER_UNNAMED_SERVICE_INFO)
    await hass.async_block_till_done(wait_background_tasks=True)

    mock_client.is_connected.side_effect = False
