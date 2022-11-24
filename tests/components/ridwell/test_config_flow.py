"""Test the Ridwell config flow."""
from unittest.mock import patch

from aioridwell.errors import InvalidCredentialsError, RidwellError
import pytest

from spencerassistant import config_entries
from spencerassistant.components.ridwell.const import DOMAIN
from spencerassistant.const import CONF_PASSWORD, CONF_USERNAME
from spencerassistant.core import spencerAssistant
from spencerassistant.data_entry_flow import FlowResultType


async def test_duplicate_error(hass: spencerAssistant, config, config_entry):
    """Test that errors are shown when duplicate entries are added."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}, data=config
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.parametrize(
    "exc,error",
    [
        (InvalidCredentialsError, "invalid_auth"),
        (RidwellError, "unknown"),
    ],
)
async def test_errors(hass: spencerAssistant, config, error, exc) -> None:
    """Test that various exceptions show the correct error."""
    with patch(
        "spencerassistant.components.ridwell.config_flow.async_get_client", side_effect=exc
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=config
        )
        assert result["type"] == FlowResultType.FORM
        assert result["errors"]["base"] == error


async def test_show_form_user(hass: spencerAssistant) -> None:
    """Test showing the form to input credentials."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] is None


async def test_step_reauth(
    hass: spencerAssistant, config, config_entry, setup_ridwell
) -> None:
    """Test a full reauth flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_REAUTH},
        data={CONF_USERNAME: "user@email.com", CONF_PASSWORD: "password"},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_PASSWORD: "password"},
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert len(hass.config_entries.async_entries()) == 1


async def test_step_user(hass: spencerAssistant, config, setup_ridwell) -> None:
    """Test that the full user step succeeds."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}, data=config
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
