"""Test the Ezviz config flow."""
from unittest.mock import patch

from pyezviz.client import PyEzvizError

from homeassistant import exceptions
from homeassistant.components.ezviz.const import (
    CONF_FFMPEG_ARGUMENTS,
    DEFAULT_FFMPEG_ARGUMENTS,
    DEFAULT_TIMEOUT,
    DOMAIN,
)
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_TIMEOUT
from homeassistant.data_entry_flow import (
    RESULT_TYPE_ABORT,
    RESULT_TYPE_CREATE_ENTRY,
    RESULT_TYPE_FORM,
)
from homeassistant.setup import async_setup_component

from . import USER_INPUT, _patch_async_setup, _patch_async_setup_entry, init_integration


async def test_user_form(hass, ezviz_config_flow):
    """Test we get the user initiated form."""
    await async_setup_component(hass, "persistent_notification", {})

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] == RESULT_TYPE_FORM
    assert result["errors"] == {}

    with _patch_async_setup() as mock_setup, _patch_async_setup_entry() as mock_setup_entry:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            USER_INPUT,
        )
        await hass.async_block_till_done()

    assert result["type"] == RESULT_TYPE_CREATE_ENTRY
    assert result["title"] == "test-username"
    assert result["data"] == {**USER_INPUT, CONF_TIMEOUT: DEFAULT_TIMEOUT}

    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


async def test_user_form_unexpected_exception(hass, ezviz_config_flow):
    """Test we handle unexpected exception."""
    ezviz_config_flow.side_effect = PyEzvizError()

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        USER_INPUT,
    )

    assert result["type"] == RESULT_TYPE_ABORT
    assert result["reason"] == "unknown"


async def test_user_form_single_instance_allowed(hass, ezviz_config_flow):
    """Test that configuring more than one instance is rejected."""
    await init_integration(hass, skip_entry_setup=True)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data=USER_INPUT,
    )
    assert result["type"] == RESULT_TYPE_ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_options_flow(hass, ezviz):
    """Test updating options."""
    with patch("homeassistant.components.ezviz.PLATFORMS", []):
        entry = await init_integration(hass)

    assert entry.options[CONF_FFMPEG_ARGUMENTS] == DEFAULT_FFMPEG_ARGUMENTS
    assert entry.options[CONF_TIMEOUT] == DEFAULT_TIMEOUT

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == RESULT_TYPE_FORM
    assert result["step_id"] == "init"

    with _patch_async_setup(), _patch_async_setup_entry():
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={CONF_FFMPEG_ARGUMENTS: "/H.264", CONF_TIMEOUT: 15},
        )
        await hass.async_block_till_done()

    assert result["type"] == RESULT_TYPE_CREATE_ENTRY
    assert result["data"][CONF_FFMPEG_ARGUMENTS] == "/H.264"
    assert result["data"][CONF_TIMEOUT] == 15


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""
