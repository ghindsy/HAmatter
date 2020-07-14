"""Test the Control4 config flow."""
from homeassistant import config_entries, setup
from homeassistant.components.control4.config_flow import CannotConnect, InvalidAuth
from homeassistant.components.control4.const import DOMAIN

from tests.async_mock import patch


async def test_form(hass):
    """Test we get the form."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["errors"] == {}

    with patch(
        "homeassistant.components.control4.config_flow.Control4Validator.authenticate",
        return_value=True,
    ), patch(
        "homeassistant.components.control4.config_flow.Control4Validator.connect_to_director",
        return_value=True,
    ), patch(
        "homeassistant.components.control4.config_flow.Control4Validator.return_controller_unique_id",
        return_value="control4_model_00AA00AA00AA",
    ), patch(
        "homeassistant.components.control4.async_setup", return_value=True
    ) as mock_setup, patch(
        "homeassistant.components.control4.async_setup_entry", return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "1.1.1.1",
                "username": "test-username",
                "password": "test-password",
            },
        )

    assert result2["type"] == "create_entry"
    assert result2["title"] == "control4_model_00AA00AA00AA"
    assert result2["data"] == {
        "host": "1.1.1.1",
        "username": "test-username",
        "password": "test-password",
        "controller_unique_id": "control4_model_00AA00AA00AA",
    }
    await hass.async_block_till_done()
    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_auth(hass):
    """Test we handle invalid auth."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.control4.config_flow.Control4Validator.authenticate",
        side_effect=InvalidAuth,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "1.1.1.1",
                "username": "test-username",
                "password": "test-password",
            },
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_form_cannot_connect(hass):
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.control4.config_flow.Control4Validator.authenticate",
        return_value=True,
    ), patch(
        "homeassistant.components.control4.config_flow.Control4Validator.connect_to_director",
        side_effect=CannotConnect,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "1.1.1.1",
                "username": "test-username",
                "password": "test-password",
            },
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "cannot_connect"}
