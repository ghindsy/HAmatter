"""Test the Garmin Connect config flow."""
from unittest.mock import patch

from garminconnect_aio import (
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)
import pytest

from homeassistant import config_entries, data_entry_flow
from homeassistant.components.garmin_connect.const import DOMAIN
from homeassistant.const import CONF_ID, CONF_PASSWORD, CONF_USERNAME

from tests.common import MockConfigEntry

MOCK_CONF = {
    CONF_ID: "my@email.address",
    CONF_USERNAME: "my@email.address",
    CONF_PASSWORD: "mypassw0rd",
}


@pytest.fixture(name="mock_garmin_connect")
def mock_garmin():
    """Mock Garmin Connect."""
    with patch(
        "homeassistant.components.garmin_connect.config_flow.Garmin",
    ) as garmin:
        garmin.return_value.login.return_value = MOCK_CONF[CONF_ID]
        yield garmin.return_value


async def test_show_form(hass):
    """Test that the form is served with no input."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["errors"] == {}
    assert result["step_id"] == config_entries.SOURCE_USER


async def test_step_user(hass):
    """Test registering an integration and finishing flow works."""

    with patch(
        "homeassistant.components.garmin_connect.Garmin.login",
        return_value="my@email.address",
    ), patch(
        "homeassistant.components.garmin_connect.async_setup_entry", return_value=True
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=MOCK_CONF
        )
    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result["data"] == MOCK_CONF


async def test_connection_error(hass, mock_garmin_connect):
    """Test for connection error."""
    mock_garmin_connect.login.side_effect = GarminConnectConnectionError("errormsg")
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}, data=MOCK_CONF
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_authentication_error(hass, mock_garmin_connect):
    """Test for authentication error."""
    mock_garmin_connect.login.side_effect = GarminConnectAuthenticationError("errormsg")
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}, data=MOCK_CONF
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_toomanyrequest_error(hass, mock_garmin_connect):
    """Test for toomanyrequests error."""
    mock_garmin_connect.login.side_effect = GarminConnectTooManyRequestsError(
        "errormsg"
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}, data=MOCK_CONF
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["errors"] == {"base": "too_many_requests"}


async def test_unknown_error(hass, mock_garmin_connect):
    """Test for unknown error."""
    mock_garmin_connect.login.side_effect = Exception
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}, data=MOCK_CONF
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["errors"] == {"base": "unknown"}


async def test_abort_if_already_setup(hass):
    """Test abort if already setup."""
    MockConfigEntry(
        domain=DOMAIN, data=MOCK_CONF, unique_id=MOCK_CONF[CONF_ID]
    ).add_to_hass(hass)
    with patch(
        "homeassistant.components.garmin_connect.config_flow.Garmin", autospec=True
    ) as garmin:
        garmin.return_value.login.return_value = MOCK_CONF[CONF_ID]
        # yield garmin.return_value

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}, data=MOCK_CONF
        )
        assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT
        assert result["reason"] == "already_configured"
