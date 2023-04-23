"""Tests for the Elmax config flow."""
from unittest.mock import patch

from elmax_api.exceptions import ElmaxBadLoginError, ElmaxBadPinError, ElmaxNetworkError

from homeassistant import config_entries, data_entry_flow
from homeassistant.components.elmax.const import (
    CONF_ELMAX_PANEL_ID,
    CONF_ELMAX_PANEL_NAME,
    CONF_ELMAX_PANEL_PIN,
    CONF_ELMAX_PASSWORD,
    CONF_ELMAX_USERNAME,
    DOMAIN,
)
from homeassistant.config_entries import SOURCE_REAUTH

from tests.common import MockConfigEntry
from tests.components.elmax import (
    MOCK_PANEL_ID,
    MOCK_PANEL_NAME,
    MOCK_PANEL_PIN,
    MOCK_PASSWORD,
    MOCK_USERNAME,
)

CONF_POLLING = "polling"


async def test_show_form(hass):
    """Test that the form is served with no input."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "user"


async def test_standard_setup(hass):
    """Test the standard setup case."""
    # Setup once.
    show_form_result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch(
        "homeassistant.components.elmax.async_setup_entry",
        return_value=True,
    ):
        login_result = await hass.config_entries.flow.async_configure(
            show_form_result["flow_id"],
            {
                CONF_ELMAX_USERNAME: MOCK_USERNAME,
                CONF_ELMAX_PASSWORD: MOCK_PASSWORD,
            },
        )
        result = await hass.config_entries.flow.async_configure(
            login_result["flow_id"],
            {
                CONF_ELMAX_PANEL_NAME: MOCK_PANEL_NAME,
                CONF_ELMAX_PANEL_PIN: MOCK_PANEL_PIN,
            },
        )
        await hass.async_block_till_done()
        assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY


async def test_one_config_allowed(hass):
    """Test that only one Elmax configuration is allowed for each panel."""
    MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_ELMAX_PANEL_ID: MOCK_PANEL_ID,
            CONF_ELMAX_USERNAME: MOCK_USERNAME,
            CONF_ELMAX_PASSWORD: MOCK_PASSWORD,
            CONF_ELMAX_PANEL_PIN: MOCK_PANEL_PIN,
        },
        unique_id=MOCK_PANEL_ID,
    ).add_to_hass(hass)

    # Attempt to add another instance of the integration for the very same panel, it must fail.
    show_form_result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    login_result = await hass.config_entries.flow.async_configure(
        show_form_result["flow_id"],
        {
            CONF_ELMAX_USERNAME: MOCK_USERNAME,
            CONF_ELMAX_PASSWORD: MOCK_PASSWORD,
        },
    )
    result = await hass.config_entries.flow.async_configure(
        login_result["flow_id"],
        {
            CONF_ELMAX_PANEL_NAME: MOCK_PANEL_NAME,
            CONF_ELMAX_PANEL_PIN: MOCK_PANEL_PIN,
        },
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT
    assert result["reason"] == "already_configured"


async def test_invalid_credentials(hass):
    """Test that invalid credentials throws an error."""
    with patch(
        "elmax_api.http.Elmax.login",
        side_effect=ElmaxBadLoginError(),
    ):
        show_form_result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        login_result = await hass.config_entries.flow.async_configure(
            show_form_result["flow_id"],
            {
                CONF_ELMAX_USERNAME: "wrong_user_name@email.com",
                CONF_ELMAX_PASSWORD: "incorrect_password",
            },
        )
        assert login_result["step_id"] == "user"
        assert login_result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert login_result["errors"] == {"base": "invalid_auth"}


async def test_connection_error(hass):
    """Test other than invalid credentials throws an error."""
    with patch(
        "elmax_api.http.Elmax.login",
        side_effect=ElmaxNetworkError(),
    ):
        show_form_result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        login_result = await hass.config_entries.flow.async_configure(
            show_form_result["flow_id"],
            {
                CONF_ELMAX_USERNAME: MOCK_USERNAME,
                CONF_ELMAX_PASSWORD: MOCK_PASSWORD,
            },
        )
        assert login_result["step_id"] == "user"
        assert login_result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert login_result["errors"] == {"base": "network_error"}


async def test_unhandled_error(hass):
    """Test unhandled exceptions."""
    with patch(
        "elmax_api.http.Elmax.get_panel_status",
        side_effect=Exception(),
    ):
        show_form_result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        login_result = await hass.config_entries.flow.async_configure(
            show_form_result["flow_id"],
            {
                CONF_ELMAX_USERNAME: MOCK_USERNAME,
                CONF_ELMAX_PASSWORD: MOCK_PASSWORD,
            },
        )
        result = await hass.config_entries.flow.async_configure(
            login_result["flow_id"],
            {
                CONF_ELMAX_PANEL_NAME: MOCK_PANEL_NAME,
                CONF_ELMAX_PANEL_PIN: MOCK_PANEL_PIN,
            },
        )
        assert result["step_id"] == "panels"
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["errors"] == {"base": "unknown"}


async def test_invalid_pin(hass):
    """Test error is thrown when a wrong pin is used to pair a panel."""
    # Simulate bad pin response.
    with patch(
        "elmax_api.http.Elmax.get_panel_status",
        side_effect=ElmaxBadPinError(),
    ):
        show_form_result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        login_result = await hass.config_entries.flow.async_configure(
            show_form_result["flow_id"],
            {
                CONF_ELMAX_USERNAME: MOCK_USERNAME,
                CONF_ELMAX_PASSWORD: MOCK_PASSWORD,
            },
        )
        result = await hass.config_entries.flow.async_configure(
            login_result["flow_id"],
            {
                CONF_ELMAX_PANEL_NAME: MOCK_PANEL_NAME,
                CONF_ELMAX_PANEL_PIN: MOCK_PANEL_PIN,
            },
        )
        assert result["step_id"] == "panels"
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["errors"] == {"base": "invalid_pin"}


async def test_no_online_panel(hass):
    """Test no-online panel is available."""
    # Simulate low-level api returns no panels.
    with patch(
        "elmax_api.http.Elmax.list_control_panels",
        return_value=[],
    ):
        show_form_result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        login_result = await hass.config_entries.flow.async_configure(
            show_form_result["flow_id"],
            {
                CONF_ELMAX_USERNAME: MOCK_USERNAME,
                CONF_ELMAX_PASSWORD: MOCK_PASSWORD,
            },
        )
        assert login_result["step_id"] == "user"
        assert login_result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert login_result["errors"] == {"base": "no_panel_online"}


async def test_show_reauth(hass):
    """Test that the reauth form shows."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_ELMAX_PANEL_ID: MOCK_PANEL_ID,
            CONF_ELMAX_USERNAME: MOCK_USERNAME,
            CONF_ELMAX_PASSWORD: MOCK_PASSWORD,
            CONF_ELMAX_PANEL_PIN: MOCK_PANEL_PIN,
        },
        unique_id=MOCK_PANEL_ID,
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": SOURCE_REAUTH,
            "unique_id": entry.unique_id,
            "entry_id": entry.entry_id,
        },
        data={
            CONF_ELMAX_PANEL_ID: MOCK_PANEL_ID,
            CONF_ELMAX_PANEL_PIN: MOCK_PANEL_PIN,
            CONF_ELMAX_USERNAME: MOCK_USERNAME,
            CONF_ELMAX_PASSWORD: MOCK_PASSWORD,
        },
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "reauth_confirm"


async def test_reauth_flow(hass):
    """Test that the reauth flow works."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_ELMAX_PANEL_ID: MOCK_PANEL_ID,
            CONF_ELMAX_USERNAME: MOCK_USERNAME,
            CONF_ELMAX_PASSWORD: MOCK_PASSWORD,
            CONF_ELMAX_PANEL_PIN: MOCK_PANEL_PIN,
        },
        unique_id=MOCK_PANEL_ID,
    )
    entry.add_to_hass(hass)

    # Trigger reauth
    with patch(
        "homeassistant.components.elmax.async_setup_entry",
        return_value=True,
    ):
        reauth_result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_REAUTH, "entry_id": entry.entry_id},
            data={
                CONF_ELMAX_PANEL_ID: MOCK_PANEL_ID,
                CONF_ELMAX_PANEL_PIN: MOCK_PANEL_PIN,
                CONF_ELMAX_USERNAME: MOCK_USERNAME,
                CONF_ELMAX_PASSWORD: MOCK_PASSWORD,
            },
        )
        result = await hass.config_entries.flow.async_configure(
            reauth_result["flow_id"],
            {
                CONF_ELMAX_PANEL_PIN: MOCK_PANEL_PIN,
                CONF_ELMAX_USERNAME: MOCK_USERNAME,
                CONF_ELMAX_PASSWORD: MOCK_PASSWORD,
            },
        )
        assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT
        await hass.async_block_till_done()
        assert result["reason"] == "reauth_successful"


async def test_reauth_panel_disappeared(hass):
    """Test that the case where panel is no longer associated with the user."""
    # Simulate a first setup
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_ELMAX_PANEL_ID: MOCK_PANEL_ID,
            CONF_ELMAX_USERNAME: MOCK_USERNAME,
            CONF_ELMAX_PASSWORD: MOCK_PASSWORD,
            CONF_ELMAX_PANEL_PIN: MOCK_PANEL_PIN,
        },
        unique_id=MOCK_PANEL_ID,
    )
    entry.add_to_hass(hass)

    # Trigger reauth
    with patch(
        "elmax_api.http.Elmax.list_control_panels",
        return_value=[],
    ):
        reauth_result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_REAUTH, "entry_id": entry.entry_id},
            data={
                CONF_ELMAX_PANEL_ID: MOCK_PANEL_ID,
                CONF_ELMAX_PANEL_PIN: MOCK_PANEL_PIN,
                CONF_ELMAX_USERNAME: MOCK_USERNAME,
                CONF_ELMAX_PASSWORD: MOCK_PASSWORD,
            },
        )
        result = await hass.config_entries.flow.async_configure(
            reauth_result["flow_id"],
            {
                CONF_ELMAX_PANEL_PIN: MOCK_PANEL_PIN,
                CONF_ELMAX_USERNAME: MOCK_USERNAME,
                CONF_ELMAX_PASSWORD: MOCK_PASSWORD,
            },
        )
        assert result["step_id"] == "reauth_confirm"
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["errors"] == {"base": "reauth_panel_disappeared"}


async def test_reauth_invalid_pin(hass):
    """Test that the case where panel is no longer associated with the user."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_ELMAX_PANEL_ID: MOCK_PANEL_ID,
            CONF_ELMAX_USERNAME: MOCK_USERNAME,
            CONF_ELMAX_PASSWORD: MOCK_PASSWORD,
            CONF_ELMAX_PANEL_PIN: MOCK_PANEL_PIN,
        },
        unique_id=MOCK_PANEL_ID,
    )
    entry.add_to_hass(hass)

    # Trigger reauth
    with patch(
        "elmax_api.http.Elmax.get_panel_status",
        side_effect=ElmaxBadPinError(),
    ):
        reauth_result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_REAUTH, "entry_id": entry.entry_id},
            data={
                CONF_ELMAX_PANEL_ID: MOCK_PANEL_ID,
                CONF_ELMAX_PANEL_PIN: MOCK_PANEL_PIN,
                CONF_ELMAX_USERNAME: MOCK_USERNAME,
                CONF_ELMAX_PASSWORD: MOCK_PASSWORD,
            },
        )
        result = await hass.config_entries.flow.async_configure(
            reauth_result["flow_id"],
            {
                CONF_ELMAX_PANEL_PIN: MOCK_PANEL_PIN,
                CONF_ELMAX_USERNAME: MOCK_USERNAME,
                CONF_ELMAX_PASSWORD: MOCK_PASSWORD,
            },
        )
        assert result["step_id"] == "reauth_confirm"
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["errors"] == {"base": "invalid_pin"}


async def test_reauth_bad_login(hass):
    """Test bad login attempt at reauth time."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_ELMAX_PANEL_ID: MOCK_PANEL_ID,
            CONF_ELMAX_USERNAME: MOCK_USERNAME,
            CONF_ELMAX_PASSWORD: MOCK_PASSWORD,
            CONF_ELMAX_PANEL_PIN: MOCK_PANEL_PIN,
        },
        unique_id=MOCK_PANEL_ID,
    )
    entry.add_to_hass(hass)

    # Trigger reauth
    with patch(
        "elmax_api.http.Elmax.login",
        side_effect=ElmaxBadLoginError(),
    ):
        reauth_result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_REAUTH, "entry_id": entry.entry_id},
            data={
                CONF_ELMAX_PANEL_ID: MOCK_PANEL_ID,
                CONF_ELMAX_PANEL_PIN: MOCK_PANEL_PIN,
                CONF_ELMAX_USERNAME: MOCK_USERNAME,
                CONF_ELMAX_PASSWORD: MOCK_PASSWORD,
            },
        )
        result = await hass.config_entries.flow.async_configure(
            reauth_result["flow_id"],
            {
                CONF_ELMAX_PANEL_PIN: MOCK_PANEL_PIN,
                CONF_ELMAX_USERNAME: MOCK_USERNAME,
                CONF_ELMAX_PASSWORD: MOCK_PASSWORD,
            },
        )
        assert result["step_id"] == "reauth_confirm"
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["errors"] == {"base": "invalid_auth"}
