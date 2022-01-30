"""Test Tautulli config flow."""
from unittest.mock import patch

from pytautulli import exceptions

from homeassistant import data_entry_flow
from homeassistant.components.tautulli.const import DEFAULT_NAME, DOMAIN
from homeassistant.config_entries import SOURCE_IMPORT, SOURCE_REAUTH, SOURCE_USER
from homeassistant.const import CONF_API_KEY, CONF_SOURCE
from homeassistant.core import HomeAssistant

from . import (
    CONF_DATA,
    CONF_IMPORT_DATA,
    NAME,
    create_mocked_tautulli,
    patch_config_flow_tautulli,
    setup_integration,
)

from tests.common import MockConfigEntry
from tests.test_util.aiohttp import AiohttpClientMocker


def _patch_setup():
    return patch("homeassistant.components.tautulli.async_setup_entry")


async def test_flow_user_single_instance_allowed(hass: HomeAssistant) -> None:
    """Test user step single instance allowed."""
    entry = MockConfigEntry(domain=DOMAIN, data=CONF_DATA)
    entry.add_to_hass(hass)

    with patch_config_flow_tautulli(await create_mocked_tautulli()):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data=CONF_IMPORT_DATA,
        )
        assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT
        assert result["reason"] == "single_instance_allowed"


async def test_flow_user(hass: HomeAssistant) -> None:
    """Test user initiated flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={CONF_SOURCE: SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    mocked_tautulli = await create_mocked_tautulli()
    with patch_config_flow_tautulli(mocked_tautulli), _patch_setup():
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=CONF_DATA,
        )
    await hass.async_block_till_done()

    assert result2["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result2["title"] == NAME
    assert result2["data"] == CONF_DATA


async def test_flow_user_cannot_connect(hass: HomeAssistant) -> None:
    """Test user initialized flow with unreachable server."""
    with patch_config_flow_tautulli(await create_mocked_tautulli()) as tautullimock:
        tautullimock.side_effect = exceptions.PyTautulliConnectionException
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={CONF_SOURCE: SOURCE_USER}, data=CONF_DATA
        )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "user"
    assert result["errors"]["base"] == "cannot_connect"


async def test_flow_user_invalid_auth(hass: HomeAssistant) -> None:
    """Test user initialized flow with invalid authentication."""
    with patch_config_flow_tautulli(await create_mocked_tautulli()) as tautullimock:
        tautullimock.side_effect = exceptions.PyTautulliAuthenticationException
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=CONF_DATA
        )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "user"
    assert result["errors"]["base"] == "invalid_auth"


async def test_flow_user_unknown_error(hass: HomeAssistant) -> None:
    """Test user initialized flow with unreachable server."""
    with patch_config_flow_tautulli(await create_mocked_tautulli()) as tautullimock:
        tautullimock.side_effect = exceptions.PyTautulliException
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={CONF_SOURCE: SOURCE_USER}, data=CONF_DATA
        )
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "user"
        assert result["errors"]["base"] == "unknown"


async def test_flow_import(hass: HomeAssistant) -> None:
    """Test import step."""
    with patch_config_flow_tautulli(await create_mocked_tautulli()), _patch_setup():
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data=CONF_IMPORT_DATA,
        )
        assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
        assert result["title"] == DEFAULT_NAME
        assert result["data"] == CONF_DATA


async def test_flow_import_single_instance_allowed(hass: HomeAssistant) -> None:
    """Test import step single instance allowed."""
    entry = MockConfigEntry(domain=DOMAIN, data=CONF_DATA)
    entry.add_to_hass(hass)

    with patch_config_flow_tautulli(await create_mocked_tautulli()):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data=CONF_IMPORT_DATA,
        )
        assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT
        assert result["reason"] == "single_instance_allowed"


async def test_flow_reauth(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test reauth flow."""
    with patch("homeassistant.components.tautulli.PLATFORMS", []):
        entry = await setup_integration(hass, aioclient_mock)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            CONF_SOURCE: SOURCE_REAUTH,
            "entry_id": entry.entry_id,
            "unique_id": entry.unique_id,
        },
        data=CONF_DATA,
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"] == {}

    new_conf = {CONF_API_KEY: "efgh"}
    CONF_DATA[CONF_API_KEY] = "efgh"
    mocked_tautulli = await create_mocked_tautulli()
    with patch_config_flow_tautulli(mocked_tautulli), _patch_setup() as mock_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=new_conf,
        )
        await hass.async_block_till_done()

    assert result2["type"] == data_entry_flow.RESULT_TYPE_ABORT
    assert result2["reason"] == "reauth_successful"
    assert entry.data == CONF_DATA
    assert len(mock_entry.mock_calls) == 1


async def test_flow_reauth_error(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test reauth flow with invalid authentication."""
    with patch("homeassistant.components.tautulli.PLATFORMS", []):
        entry = await setup_integration(hass, aioclient_mock)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": SOURCE_REAUTH,
            "entry_id": entry.entry_id,
            "unique_id": entry.unique_id,
        },
    )
    with patch_config_flow_tautulli(await create_mocked_tautulli()) as tautullimock:
        tautullimock.side_effect = exceptions.PyTautulliAuthenticationException
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_API_KEY: "efgh"},
        )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"]["base"] == "invalid_auth"
