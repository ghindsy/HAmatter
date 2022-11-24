"""Test the Ruuvitag config flow."""

from unittest.mock import patch

import pytest

from spencerassistant import config_entries
from spencerassistant.components.ruuvitag_ble.const import DOMAIN
from spencerassistant.data_entry_flow import FlowResultType

from .fixtures import CONFIGURED_NAME, NOT_RUUVITAG_SERVICE_INFO, RUUVITAG_SERVICE_INFO

from tests.common import MockConfigEntry


@pytest.fixture(autouse=True)
def mock_bluetooth(enable_bluetooth):
    """Mock bluetooth for all tests in this module."""


async def test_async_step_bluetooth_valid_device(hass):
    """Test discovery via bluetooth with a valid device."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=RUUVITAG_SERVICE_INFO,
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "bluetooth_confirm"
    with patch(
        "spencerassistant.components.ruuvitag_ble.async_setup_entry", return_value=True
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )
    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == CONFIGURED_NAME
    assert result2["result"].unique_id == RUUVITAG_SERVICE_INFO.address


async def test_async_step_bluetooth_not_ruuvitag(hass):
    """Test discovery via bluetooth not ruuvitag."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=NOT_RUUVITAG_SERVICE_INFO,
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "not_supported"


async def test_async_step_user_no_devices_found(hass):
    """Test setup from service info cache with no devices found."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"


async def test_async_step_user_with_found_devices(hass):
    """Test setup from service info cache with devices found."""
    with patch(
        "spencerassistant.components.ruuvitag_ble.config_flow.async_discovered_service_info",
        return_value=[RUUVITAG_SERVICE_INFO],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    with patch(
        "spencerassistant.components.ruuvitag_ble.async_setup_entry", return_value=True
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"address": RUUVITAG_SERVICE_INFO.address},
        )
    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == CONFIGURED_NAME
    assert result2["result"].unique_id == RUUVITAG_SERVICE_INFO.address


async def test_async_step_user_device_added_between_steps(hass):
    """Test the device gets added via another flow between steps."""
    with patch(
        "spencerassistant.components.ruuvitag_ble.config_flow.async_discovered_service_info",
        return_value=[RUUVITAG_SERVICE_INFO],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=RUUVITAG_SERVICE_INFO.address,
    )
    entry.add_to_hass(hass)

    with patch(
        "spencerassistant.components.ruuvitag_ble.async_setup_entry", return_value=True
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"address": RUUVITAG_SERVICE_INFO.address},
        )
    assert result2["type"] == FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


async def test_async_step_user_with_found_devices_already_setup(hass):
    """Test setup from service info cache with devices found."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=RUUVITAG_SERVICE_INFO.address,
    )
    entry.add_to_hass(hass)

    with patch(
        "spencerassistant.components.ruuvitag_ble.config_flow.async_discovered_service_info",
        return_value=[RUUVITAG_SERVICE_INFO],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"


async def test_async_step_bluetooth_devices_already_setup(hass):
    """Test we can't start a flow if there is already a config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=RUUVITAG_SERVICE_INFO.address,
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=RUUVITAG_SERVICE_INFO,
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_async_step_bluetooth_already_in_progress(hass):
    """Test we can't start a flow for the same device twice."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=RUUVITAG_SERVICE_INFO,
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "bluetooth_confirm"

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=RUUVITAG_SERVICE_INFO,
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_in_progress"


async def test_async_step_user_takes_precedence_over_discovery(hass):
    """Test manual setup takes precedence over discovery."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=RUUVITAG_SERVICE_INFO,
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "bluetooth_confirm"

    with patch(
        "spencerassistant.components.ruuvitag_ble.config_flow.async_discovered_service_info",
        return_value=[RUUVITAG_SERVICE_INFO],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        assert result["type"] == FlowResultType.FORM

    with patch(
        "spencerassistant.components.ruuvitag_ble.async_setup_entry", return_value=True
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"address": RUUVITAG_SERVICE_INFO.address},
        )
    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == CONFIGURED_NAME
    assert result2["data"] == {}
    assert result2["result"].unique_id == RUUVITAG_SERVICE_INFO.address
