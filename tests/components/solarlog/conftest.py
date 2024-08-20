"""Test helpers."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.components.solarlog.const import DOMAIN as SOLARLOG_DOMAIN
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant

from .const import HOST, NAME

from tests.common import (
    MockConfigEntry,
    load_json_object_fixture,
    mock_device_registry,
    mock_registry,
)


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Mock a config entry."""
    return MockConfigEntry(
        domain=SOLARLOG_DOMAIN,
        title="solarlog",
        data={
            CONF_HOST: HOST,
            CONF_NAME: NAME,
            "extended_data": True,
        },
        options={
            "devices": {
                0: True,
                1: False,
            }
        },
        minor_version=2,
        entry_id="ce5f5431554d101905d31797e1232da8",
    )


@pytest.fixture
def mock_solarlog_connector():
    """Build a fixture for the SolarLog API that connects successfully and returns one device."""

    mock_solarlog_api = AsyncMock()
    mock_solarlog_api.test_connection = AsyncMock(return_value=True)

    data = {
        "devices": {
            0: {"consumption_total": 354687, "current_power": 5},
        }
    }
    data |= load_json_object_fixture("solarlog_data.json", SOLARLOG_DOMAIN)

    mock_solarlog_api.update_data.return_value = data
    mock_solarlog_api.device_list.return_value = {
        0: {"name": "Inverter 1"},
        1: {"name": "Inverter 2"},
    }
    mock_solarlog_api.device_name = {0: "Inverter 1", 1: "Inverter 2"}.get
    mock_solarlog_api.device_enabled = {0: True, 1: False}.get
    # mock_solarlog_api.device_enabled = lambda *args: enabled_devices(*args)
    mock_solarlog_api.client.get_device_list.return_value = {
        0: {"name": "Inverter 1"},
        1: {"name": "Inverter 2"},
    }

    with (
        patch(
            "homeassistant.components.solarlog.coordinator.SolarLogConnector",
            autospec=True,
            return_value=mock_solarlog_api,
        ),
        patch(
            "homeassistant.components.solarlog.config_flow.SolarLogConnector",
            autospec=True,
            return_value=mock_solarlog_api,
        ),
    ):
        yield mock_solarlog_api


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Override async_setup_entry."""
    with patch(
        "homeassistant.components.solarlog.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture(name="test_connect")
def mock_test_connection():
    """Mock a successful _test_connection."""
    with patch(
        "homeassistant.components.solarlog.config_flow.SolarLogConfigFlow._test_connection",
        return_value=True,
    ):
        yield


@pytest.fixture(name="update_listener")
def mock_update_listener():
    """Override update listener."""
    with patch(
        "homeassistant.components.solarlog.update_listener"
    ) as mock_update_listener:
        yield mock_update_listener


@pytest.fixture(name="device_reg")
def device_reg_fixture(hass: HomeAssistant):
    """Return an empty, loaded, registry."""
    return mock_device_registry(hass)


@pytest.fixture(name="entity_reg")
def entity_reg_fixture(hass: HomeAssistant):
    """Return an empty, loaded, registry."""
    return mock_registry(hass)
