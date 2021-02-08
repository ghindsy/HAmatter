"""Test the Rituals Perfume Genie config flow."""
from unittest.mock import patch

from pyrituals import AuthenticationException

from homeassistant import config_entries
from homeassistant.components.rituals_perfume_genie.const import ACCOUNT_HASH, DOMAIN
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

TEST_EMAIL = "rituals@example.com"
VALID_PASSWORD = "passw0rd"
WRONG_PASSWORD = "wrong-passw0rd"


async def test_form(hass):
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["errors"] is None

    with patch(
        "homeassistant.components.rituals_perfume_genie.async_setup", return_value=True
    ) as mock_setup, patch(
        "homeassistant.components.rituals_perfume_genie.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_EMAIL: TEST_EMAIL,
                CONF_PASSWORD: VALID_PASSWORD,
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == "create_entry"
    assert result2["title"] == TEST_EMAIL
    assert isinstance(result2["data"][ACCOUNT_HASH], str)
    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_auth(hass):
    """Test we handle invalid auth."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.rituals_perfume_genie.config_flow.Account.authenticate",
        side_effect=AuthenticationException,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_EMAIL: TEST_EMAIL,
                CONF_PASSWORD: WRONG_PASSWORD,
            },
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "invalid_auth"}
