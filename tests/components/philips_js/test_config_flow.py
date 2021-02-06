"""Test the Philips TV config flow."""
from unittest.mock import patch

from pytest import fixture

from homeassistant import config_entries
from homeassistant.components.philips_js.const import DOMAIN

from . import (
    MOCK_CONFIG,
    MOCK_CONFIG_PAIRED,
    MOCK_IMPORT,
    MOCK_PASSWORD,
    MOCK_SYSTEM_UNPAIRED,
    MOCK_USERINPUT,
    MOCK_USERNAME,
)


@fixture(autouse=True)
def mock_setup():
    """Disable component setup."""
    with patch(
        "homeassistant.components.philips_js.async_setup", return_value=True
    ) as mock_setup:
        yield mock_setup


@fixture(autouse=True)
def mock_setup_entry():
    """Disable component setup."""
    with patch(
        "homeassistant.components.philips_js.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        yield mock_setup_entry


async def test_import(hass, mock_setup, mock_setup_entry):
    """Test we get an item on import."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data=MOCK_IMPORT,
    )

    assert result["type"] == "create_entry"
    assert result["title"] == "Philips TV (1234567890)"
    assert result["data"] == MOCK_CONFIG
    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


async def test_import_exist(hass, mock_config_entry):
    """Test we get an item on import."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data=MOCK_IMPORT,
    )

    assert result["type"] == "abort"
    assert result["reason"] == "already_configured"


async def test_form(hass, mock_setup, mock_setup_entry):
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["errors"] == {}

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        MOCK_USERINPUT,
    )
    await hass.async_block_till_done()

    assert result2["type"] == "create_entry"
    assert result2["title"] == "Philips TV (1234567890)"
    assert result2["data"] == MOCK_CONFIG
    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_cannot_connect(hass, mock_tv):
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_tv.system = None
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], MOCK_USERINPUT
    )

    assert result["type"] == "form"
    assert result["errors"] == {"base": "cannot_connect"}


async def test_form_unexpected_error(hass, mock_tv):
    """Test we handle unexpected exceptions."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_tv.getSystem.side_effect = Exception("Unexpected exception")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], MOCK_USERINPUT
    )

    assert result["type"] == "form"
    assert result["errors"] == {"base": "unknown"}


async def test_pairing(hass, mock_tv, mock_setup, mock_setup_entry):
    """Test we get the form."""

    mock_tv.system = MOCK_SYSTEM_UNPAIRED
    mock_tv.pairing_type = "digest_auth_pairing"
    mock_tv.api_version = 6
    mock_tv.api_version_detected = 6
    mock_tv.secured_transport = True

    mock_tv.pairRequest.return_value = {}
    mock_tv.pairGrant.return_value = MOCK_USERNAME, MOCK_PASSWORD

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        MOCK_USERINPUT,
    )
    await hass.async_block_till_done()

    assert result["type"] == "form"
    assert result["errors"] == {}

    mock_tv.setTransport.assert_called_with(True, 6)
    mock_tv.pairRequest.assert_called()

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"pin": "1234"}
    )
    await hass.async_block_till_done()

    assert result["type"] == "create_entry"
    assert result["title"] == "55PUS7181/12 (None)"
    assert result["data"] == MOCK_CONFIG_PAIRED

    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1
