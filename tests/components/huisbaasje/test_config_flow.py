"""Test the Huisbaasje config flow."""
from homeassistant import config_entries, setup
from homeassistant.components.huisbaasje.config_flow import (
    HuisbaasjeConnectionException,
    HuisbaasjeException,
)
from homeassistant.components.huisbaasje.const import DOMAIN

from tests.async_mock import patch


async def test_form(hass):
    """Test we get the form."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["errors"] == {}

    with patch("huisbaasje.Huisbaasje.authenticate", return_value=None,), patch(
        "huisbaasje.Huisbaasje.get_user_id",
        return_value="test-id",
    ), patch(
        "homeassistant.components.huisbaasje.async_setup", return_value=True
    ) as mock_setup, patch(
        "homeassistant.components.huisbaasje.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "test-username",
                "password": "test-password",
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == "create_entry"
    assert result2["title"] == "test-username"
    assert result2["data"] == {
        "id": "test-id",
        "username": "test-username",
        "password": "test-password",
    }
    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_auth(hass):
    """Test we handle invalid auth."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "huisbaasje.Huisbaasje.authenticate",
        side_effect=HuisbaasjeException,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
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
        "huisbaasje.Huisbaasje.authenticate",
        side_effect=HuisbaasjeConnectionException,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "test-username",
                "password": "test-password",
            },
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "connection_exception"}
