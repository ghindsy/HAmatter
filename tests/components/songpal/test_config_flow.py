"""Test the songpal config flow."""
from asynctest import MagicMock, patch
from songpal import SongpalException

from homeassistant.components import ssdp
from homeassistant.components.songpal.const import CONF_ENDPOINT, CONF_MODEL, DOMAIN
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.data_entry_flow import (
    RESULT_TYPE_ABORT,
    RESULT_TYPE_CREATE_ENTRY,
    RESULT_TYPE_FORM,
)

from tests.common import MockConfigEntry

UDN = "uuid:1234"
FRIENDLY_NAME = "friendly name"
HOST = "0.0.0.0"
ENDPOINT = f"http://{HOST}:10000/sony"
MODEL = "model name"

SSDP_DATA = {
    ssdp.ATTR_UPNP_UDN: UDN,
    ssdp.ATTR_UPNP_FRIENDLY_NAME: FRIENDLY_NAME,
    ssdp.ATTR_SSDP_LOCATION: f"http://{HOST}:52323/dmr.xml",
    ssdp.ATTR_UPNP_MODEL_NAME: MODEL,
    "X_ScalarWebAPI_DeviceInfo": {"X_ScalarWebAPI_BaseURL": ENDPOINT},
}

CONF_DATA = {
    CONF_NAME: FRIENDLY_NAME,
    CONF_ENDPOINT: ENDPOINT,
    CONF_MODEL: None,
}


async def _async_return_value():
    pass


def _connection_exception():
    raise SongpalException("Unable to do POST request: ")


def _create_mocked_device(get_supported_methods=None):
    mocked_device = MagicMock()
    type(mocked_device).get_supported_methods = MagicMock(
        side_effect=get_supported_methods, return_value=_async_return_value(),
    )
    return mocked_device


def _patch_config_flow_device(mocked_device):
    return patch(
        "homeassistant.components.songpal.config_flow.Device",
        return_value=mocked_device,
    )


async def test_flow_ssdp(hass):
    """Test working ssdp flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "ssdp"}, data=SSDP_DATA,
    )
    assert result["type"] == "form"
    assert result["step_id"] == "init"
    assert result["description_placeholders"] == {
        CONF_NAME: FRIENDLY_NAME,
        CONF_HOST: HOST,
    }

    flow = next(
        flow
        for flow in hass.config_entries.flow.async_progress()
        if flow["flow_id"] == result["flow_id"]
    )
    assert flow["context"]["unique_id"] == ENDPOINT

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={}
    )
    assert result["type"] == RESULT_TYPE_CREATE_ENTRY
    assert result["title"] == FRIENDLY_NAME
    conf_data = CONF_DATA.copy()
    conf_data[CONF_MODEL] = MODEL
    assert result["data"] == conf_data


async def test_flow_user(hass):
    """Test working user initialized flow."""
    mocked_device = _create_mocked_device()

    with _patch_config_flow_device(mocked_device):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"},
        )
        assert result["type"] == RESULT_TYPE_FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {}

        next(
            flow
            for flow in hass.config_entries.flow.async_progress()
            if flow["flow_id"] == result["flow_id"]
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_NAME: FRIENDLY_NAME, CONF_ENDPOINT: ENDPOINT},
        )
        assert result["type"] == RESULT_TYPE_CREATE_ENTRY
        assert result["title"] == FRIENDLY_NAME
        assert result["data"] == CONF_DATA

    mocked_device.get_supported_methods.assert_called_once()


async def test_flow_import(hass):
    """Test working import flow."""
    mocked_device = _create_mocked_device()

    with _patch_config_flow_device(mocked_device):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "import"}, data=CONF_DATA
        )
        assert result["type"] == RESULT_TYPE_CREATE_ENTRY
        assert result["title"] == FRIENDLY_NAME
        assert result["data"] == CONF_DATA

    mocked_device.get_supported_methods.assert_called_once()


def _create_mock_config_entry(hass):
    MockConfigEntry(domain=DOMAIN, unique_id="uuid:0000", data=CONF_DATA,).add_to_hass(
        hass
    )


async def test_sddp_exist(hass):
    """Test discovering existed device."""
    _create_mock_config_entry(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "ssdp"}, data=SSDP_DATA,
    )
    assert result["type"] == RESULT_TYPE_ABORT
    assert result["reason"] == "already_configured"


async def test_user_exist(hass):
    """Test user adding existed device."""
    mocked_device = _create_mocked_device()
    _create_mock_config_entry(hass)

    with _patch_config_flow_device(mocked_device):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}, data=CONF_DATA
        )
        assert result["type"] == RESULT_TYPE_ABORT
        assert result["reason"] == "already_configured"

    mocked_device.get_supported_methods.assert_called_once()


async def test_import_exist(hass):
    """Test importing existed device."""
    mocked_device = _create_mocked_device()
    _create_mock_config_entry(hass)

    with _patch_config_flow_device(mocked_device):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "import"}, data=CONF_DATA
        )
        assert result["type"] == RESULT_TYPE_ABORT
        assert result["reason"] == "already_configured"


async def test_user_invalid(hass):
    """Test using adding invalid config."""
    mocked_device = _create_mocked_device(_connection_exception)
    _create_mock_config_entry(hass)

    with _patch_config_flow_device(mocked_device):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}, data=CONF_DATA
        )
        assert result["type"] == RESULT_TYPE_FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {"base": "connection"}

    mocked_device.get_supported_methods.assert_called_once()


async def test_import_invalid(hass):
    """Test importing invalid config."""
    mocked_device = _create_mocked_device(_connection_exception)
    _create_mock_config_entry(hass)

    with _patch_config_flow_device(mocked_device):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "import"}, data=CONF_DATA
        )
        assert result["type"] == RESULT_TYPE_ABORT
        assert result["reason"] == "connection"

    mocked_device.get_supported_methods.assert_called_once()
