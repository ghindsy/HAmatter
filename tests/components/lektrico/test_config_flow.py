"""Tests for the Lektrico Charging Station config flow."""

import dataclasses
from ipaddress import ip_address

from lektricowifi import DeviceConnectionError

from homeassistant.components.lektrico.const import DOMAIN
from homeassistant.config_entries import SOURCE_USER, SOURCE_ZEROCONF
from homeassistant.const import (
    ATTR_HW_VERSION,
    ATTR_SERIAL_NUMBER,
    CONF_HOST,
    CONF_NAME,
    CONF_TYPE,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .conftest import (
    MOCKED_DEVICE_BOARD_REV,
    MOCKED_DEVICE_IP_ADDRESS,
    MOCKED_DEVICE_SERIAL_NUMBER,
    MOCKED_DEVICE_TYPE,
    MOCKED_DEVICE_ZEROCONF_DATA,
)

from tests.common import MockConfigEntry


async def test_user_setup(
    hass: HomeAssistant, mock_device_config, mock_setup_entry
) -> None:
    """Test manually setting up."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == SOURCE_USER
    assert "flow_id" in result

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: MOCKED_DEVICE_IP_ADDRESS,
        },
    )
    await hass.async_block_till_done()

    assert result.get("type") is FlowResultType.CREATE_ENTRY
    assert result.get("title") == f"{MOCKED_DEVICE_TYPE}_{MOCKED_DEVICE_SERIAL_NUMBER}"
    assert result.get("data") == {
        CONF_HOST: MOCKED_DEVICE_IP_ADDRESS,
        CONF_NAME: f"{MOCKED_DEVICE_TYPE}_{MOCKED_DEVICE_SERIAL_NUMBER}",
        ATTR_SERIAL_NUMBER: MOCKED_DEVICE_SERIAL_NUMBER,
        CONF_TYPE: MOCKED_DEVICE_TYPE,
        ATTR_HW_VERSION: MOCKED_DEVICE_BOARD_REV,
    }
    assert "result" in result
    assert len(mock_setup_entry.mock_calls) == 1


async def test_user_setup_already_exists(
    hass: HomeAssistant, mock_device_config
) -> None:
    """Test manually setting up when the device already exists."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: MOCKED_DEVICE_IP_ADDRESS,
        },
        unique_id=MOCKED_DEVICE_SERIAL_NUMBER,
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert not result["errors"]

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: MOCKED_DEVICE_IP_ADDRESS,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_user_setup_device_offline(
    hass: HomeAssistant, mock_device_config
) -> None:
    """Test manually setting up when device is offline."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert not result["errors"]

    mock_device_config.side_effect = DeviceConnectionError
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: MOCKED_DEVICE_IP_ADDRESS,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_HOST: "cannot_connect"}


async def test_discovered_zeroconf(
    hass: HomeAssistant, mock_device_config, mock_setup_entry
) -> None:
    """Test we can setup when discovered from zeroconf."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_ZEROCONF},
        data=MOCKED_DEVICE_ZEROCONF_DATA,
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    result2 = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["data"] == {
        CONF_HOST: MOCKED_DEVICE_IP_ADDRESS,
        CONF_NAME: f"{MOCKED_DEVICE_TYPE}_{MOCKED_DEVICE_SERIAL_NUMBER}",
        ATTR_SERIAL_NUMBER: MOCKED_DEVICE_SERIAL_NUMBER,
        CONF_TYPE: MOCKED_DEVICE_TYPE,
        ATTR_HW_VERSION: MOCKED_DEVICE_BOARD_REV,
    }
    assert result2["title"] == f"{MOCKED_DEVICE_TYPE}_{MOCKED_DEVICE_SERIAL_NUMBER}"

    entry = hass.config_entries.async_entries(DOMAIN)[0]
    zc_data_new_ip = dataclasses.replace(MOCKED_DEVICE_ZEROCONF_DATA)
    zc_data_new_ip.ip_address = ip_address(MOCKED_DEVICE_IP_ADDRESS)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_ZEROCONF},
        data=zc_data_new_ip,
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.data[CONF_HOST] == MOCKED_DEVICE_IP_ADDRESS


async def test_discovered_zeroconf_device_connection_error(
    hass: HomeAssistant, mock_device_config
) -> None:
    """Test we can setup when discovered from zeroconf but device went offline."""

    mock_device_config.side_effect = DeviceConnectionError
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_ZEROCONF},
        data=MOCKED_DEVICE_ZEROCONF_DATA,
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_HOST: "cannot_connect"}
