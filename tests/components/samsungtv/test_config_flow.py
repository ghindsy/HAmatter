"""Tests for Samsung TV config flow."""
from unittest.mock import Mock, PropertyMock, call, patch

from samsungctl.exceptions import AccessDenied, UnhandledResponse
from samsungtvws.exceptions import ConnectionFailure
from websocket import WebSocketProtocolException

from homeassistant import config_entries
from homeassistant.components.samsungtv.const import (
    ATTR_PROPERTIES,
    CONF_MANUFACTURER,
    CONF_MODEL,
    DOMAIN,
    RESULT_AUTH_MISSING,
    RESULT_CANNOT_CONNECT,
    RESULT_NOT_SUPPORTED,
    TIMEOUT_REQUEST,
    TIMEOUT_WEBSOCKET,
)
from homeassistant.components.ssdp import (
    ATTR_SSDP_LOCATION,
    ATTR_UPNP_FRIENDLY_NAME,
    ATTR_UPNP_MANUFACTURER,
    ATTR_UPNP_MODEL_NAME,
    ATTR_UPNP_UDN,
)
from homeassistant.const import (
    CONF_HOST,
    CONF_ID,
    CONF_IP_ADDRESS,
    CONF_MAC,
    CONF_METHOD,
    CONF_NAME,
    CONF_PORT,
    CONF_TOKEN,
)
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from tests.common import MockConfigEntry
from tests.components.samsungtv.conftest import (
    RESULT_ALREADY_CONFIGURED,
    RESULT_ALREADY_IN_PROGRESS,
)

MOCK_USER_DATA = {CONF_HOST: "fake_host", CONF_NAME: "fake_name"}
MOCK_SSDP_DATA = {
    ATTR_SSDP_LOCATION: "https://fake_host:12345/test",
    ATTR_UPNP_FRIENDLY_NAME: "[TV] fake_name",
    ATTR_UPNP_MANUFACTURER: "Samsung fake_manufacturer",
    ATTR_UPNP_MODEL_NAME: "fake_model",
    ATTR_UPNP_UDN: "uuid:0d1cef00-00dc-1000-9c80-4844f7b172de",
}
MOCK_SSDP_DATA_NOPREFIX = {
    ATTR_SSDP_LOCATION: "http://fake2_host:12345/test",
    ATTR_UPNP_FRIENDLY_NAME: "fake2_name",
    ATTR_UPNP_MANUFACTURER: "Samsung fake2_manufacturer",
    ATTR_UPNP_MODEL_NAME: "fake2_model",
    ATTR_UPNP_UDN: "uuid:0d1cef00-00dc-1000-9c80-4844f7b172df",
}
MOCK_SSDP_DATA_WRONGMODEL = {
    ATTR_SSDP_LOCATION: "http://fake2_host:12345/test",
    ATTR_UPNP_FRIENDLY_NAME: "fake2_name",
    ATTR_UPNP_MANUFACTURER: "fake2_manufacturer",
    ATTR_UPNP_MODEL_NAME: "HW-Qfake",
    ATTR_UPNP_UDN: "uuid:0d1cef00-00dc-1000-9c80-4844f7b172df",
}
MOCK_ZEROCONF_DATA = {
    CONF_HOST: "fake_host",
    CONF_PORT: 1234,
    ATTR_PROPERTIES: {
        "deviceid": "fake_mac",
        "manufacturer": "fake_manufacturer",
        "model": "fake_model",
        "serialNumber": "fake_serial",
    },
}
MOCK_OLD_ENTRY = {
    CONF_HOST: "fake_host",
    CONF_ID: "0d1cef00-00dc-1000-9c80-4844f7b172de_old",
    CONF_IP_ADDRESS: "fake_ip_old",
    CONF_METHOD: "legacy",
    CONF_PORT: None,
}

AUTODETECT_LEGACY = {
    "name": "HomeAssistant",
    "description": "HomeAssistant",
    "id": "ha.component.samsung",
    "method": "legacy",
    "port": None,
    "host": "fake_host",
    "timeout": TIMEOUT_REQUEST,
}
AUTODETECT_WEBSOCKET_PLAIN = {
    "host": "fake_host",
    "name": "HomeAssistant",
    "port": 8001,
    "timeout": TIMEOUT_REQUEST,
    "token": None,
}
AUTODETECT_WEBSOCKET_SSL = {
    "host": "fake_host",
    "name": "HomeAssistant",
    "port": 8002,
    "timeout": TIMEOUT_REQUEST,
    "token": None,
}
DEVICEINFO_WEBSOCKET_SSL = {
    "host": "fake_host",
    "name": "HomeAssistant",
    "port": 8002,
    "timeout": TIMEOUT_WEBSOCKET,
    "token": "123456789",
}


async def test_user_legacy(hass: HomeAssistant, remote: Mock):
    """Test starting a flow by user."""
    # show form
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["step_id"] == "user"

    # entry was added
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_USER_DATA
    )
    # legacy tv entry created
    assert result["type"] == "create_entry"
    assert result["title"] == "fake_name"
    assert result["data"][CONF_HOST] == "fake_host"
    assert result["data"][CONF_NAME] == "fake_name"
    assert result["data"][CONF_METHOD] == "legacy"
    assert result["data"][CONF_MANUFACTURER] is None
    assert result["data"][CONF_MODEL] is None
    assert result["result"].unique_id is None


async def test_user_websocket(hass: HomeAssistant, remotews: Mock):
    """Test starting a flow by user."""
    with patch(
        "homeassistant.components.samsungtv.bridge.Remote", side_effect=OSError("Boom")
    ):
        # show form
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == "form"
        assert result["step_id"] == "user"

        # entry was added
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=MOCK_USER_DATA
        )
        # websocket tv entry created
        assert result["type"] == "create_entry"
        assert result["title"] == "Living Room (82GXARRS)"
        assert result["data"][CONF_HOST] == "fake_host"
        assert result["data"][CONF_NAME] == "Living Room"
        assert result["data"][CONF_METHOD] == "websocket"
        assert result["data"][CONF_MANUFACTURER] == "Samsung"
        assert result["data"][CONF_MODEL] == "82GXARRS"
        assert result["result"].unique_id == "be9554b9-c9fb-41f4-8920-22da015376a4"


async def test_user_legacy_missing_auth(hass: HomeAssistant, remote: Mock):
    """Test starting a flow by user with authentication."""
    with patch(
        "homeassistant.components.samsungtv.bridge.Remote",
        side_effect=AccessDenied("Boom"),
    ):
        # legacy device missing authentication
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=MOCK_USER_DATA
        )
        assert result["type"] == "abort"
        assert result["reason"] == RESULT_AUTH_MISSING


async def test_user_legacy_not_supported(hass: HomeAssistant, remote: Mock):
    """Test starting a flow by user for not supported device."""
    with patch(
        "homeassistant.components.samsungtv.bridge.Remote",
        side_effect=UnhandledResponse("Boom"),
    ):
        # legacy device not supported
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=MOCK_USER_DATA
        )
        assert result["type"] == "abort"
        assert result["reason"] == RESULT_NOT_SUPPORTED


async def test_user_websocket_not_supported(hass: HomeAssistant, remotews: Mock):
    """Test starting a flow by user for not supported device."""
    with patch(
        "homeassistant.components.samsungtv.bridge.Remote",
        side_effect=OSError("Boom"),
    ), patch(
        "homeassistant.components.samsungtv.bridge.SamsungTVWS",
        side_effect=WebSocketProtocolException("Boom"),
    ):
        # websocket device not supported
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=MOCK_USER_DATA
        )
        assert result["type"] == "abort"
        assert result["reason"] == RESULT_NOT_SUPPORTED


async def test_user_not_successful(hass: HomeAssistant, remotews: Mock):
    """Test starting a flow by user but no connection found."""
    with patch(
        "homeassistant.components.samsungtv.bridge.Remote",
        side_effect=OSError("Boom"),
    ), patch(
        "homeassistant.components.samsungtv.bridge.SamsungTVWS",
        side_effect=OSError("Boom"),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=MOCK_USER_DATA
        )
        assert result["type"] == "abort"
        assert result["reason"] == RESULT_CANNOT_CONNECT


async def test_user_not_successful_2(hass: HomeAssistant, remotews: Mock):
    """Test starting a flow by user but no connection found."""
    with patch(
        "homeassistant.components.samsungtv.bridge.Remote",
        side_effect=OSError("Boom"),
    ), patch(
        "homeassistant.components.samsungtv.bridge.SamsungTVWS",
        side_effect=ConnectionFailure("Boom"),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=MOCK_USER_DATA
        )
        assert result["type"] == "abort"
        assert result["reason"] == RESULT_CANNOT_CONNECT


async def test_ssdp(hass: HomeAssistant, remote: Mock):
    """Test starting a flow from discovery."""

    # confirm to add the entry
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_SSDP}, data=MOCK_SSDP_DATA
    )
    assert result["type"] == "form"
    assert result["step_id"] == "confirm"

    # entry was added
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input="whatever"
    )
    assert result["type"] == "create_entry"
    assert result["title"] == "fake_model"
    assert result["data"][CONF_HOST] == "fake_host"
    assert result["data"][CONF_NAME] == "fake_model"
    assert result["data"][CONF_MANUFACTURER] == "Samsung fake_manufacturer"
    assert result["data"][CONF_MODEL] == "fake_model"
    assert result["result"].unique_id == "0d1cef00-00dc-1000-9c80-4844f7b172de"


async def test_ssdp_noprefix(hass: HomeAssistant, remote: Mock):
    """Test starting a flow from discovery without prefixes."""

    # confirm to add the entry
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_SSDP},
        data=MOCK_SSDP_DATA_NOPREFIX,
    )
    assert result["type"] == "form"
    assert result["step_id"] == "confirm"

    # entry was added
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input="whatever"
    )
    assert result["type"] == "create_entry"
    assert result["title"] == "fake2_model"
    assert result["data"][CONF_HOST] == "fake2_host"
    assert result["data"][CONF_NAME] == "fake2_model"
    assert result["data"][CONF_MANUFACTURER] == "Samsung fake2_manufacturer"
    assert result["data"][CONF_MODEL] == "fake2_model"
    assert result["result"].unique_id == "0d1cef00-00dc-1000-9c80-4844f7b172df"


async def test_ssdp_legacy_missing_auth(hass: HomeAssistant, remote: Mock):
    """Test starting a flow from discovery with authentication."""
    with patch(
        "homeassistant.components.samsungtv.bridge.Remote",
        side_effect=AccessDenied("Boom"),
    ):

        # confirm to add the entry
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_SSDP}, data=MOCK_SSDP_DATA
        )
        assert result["type"] == "form"
        assert result["step_id"] == "confirm"

        # missing authentication
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input="whatever"
        )
        assert result["type"] == "abort"
        assert result["reason"] == RESULT_AUTH_MISSING


async def test_ssdp_legacy_not_supported(hass: HomeAssistant, remote: Mock):
    """Test starting a flow from discovery for not supported device."""
    with patch(
        "homeassistant.components.samsungtv.bridge.Remote",
        side_effect=UnhandledResponse("Boom"),
    ):

        # confirm to add the entry
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_SSDP}, data=MOCK_SSDP_DATA
        )
        assert result["type"] == "form"
        assert result["step_id"] == "confirm"

        # device not supported
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input="whatever"
        )
        assert result["type"] == "abort"
        assert result["reason"] == RESULT_NOT_SUPPORTED


async def test_ssdp_websocket_not_supported(hass: HomeAssistant, remote: Mock):
    """Test starting a flow from discovery for not supported device."""
    with patch(
        "homeassistant.components.samsungtv.bridge.Remote",
        side_effect=OSError("Boom"),
    ), patch(
        "homeassistant.components.samsungtv.bridge.SamsungTVWS",
        side_effect=WebSocketProtocolException("Boom"),
    ):
        # confirm to add the entry
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_SSDP}, data=MOCK_SSDP_DATA
        )
        assert result["type"] == "form"
        assert result["step_id"] == "confirm"

        # device not supported
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input="whatever"
        )
        assert result["type"] == "abort"
        assert result["reason"] == RESULT_NOT_SUPPORTED


async def test_ssdp_model_not_supported(hass: HomeAssistant, remote: Mock):
    """Test starting a flow from discovery."""

    # confirm to add the entry
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_SSDP},
        data=MOCK_SSDP_DATA_WRONGMODEL,
    )
    assert result["type"] == "abort"
    assert result["reason"] == RESULT_NOT_SUPPORTED


async def test_ssdp_not_successful(hass: HomeAssistant, remote: Mock):
    """Test starting a flow from discovery but no device found."""
    with patch(
        "homeassistant.components.samsungtv.bridge.Remote",
        side_effect=OSError("Boom"),
    ), patch(
        "homeassistant.components.samsungtv.bridge.SamsungTVWS",
        side_effect=OSError("Boom"),
    ):

        # confirm to add the entry
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_SSDP}, data=MOCK_SSDP_DATA
        )
        assert result["type"] == "form"
        assert result["step_id"] == "confirm"

        # device not found
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input="whatever"
        )
        assert result["type"] == "abort"
        assert result["reason"] == RESULT_CANNOT_CONNECT


async def test_ssdp_not_successful_2(hass: HomeAssistant, remote: Mock):
    """Test starting a flow from discovery but no device found."""
    with patch(
        "homeassistant.components.samsungtv.bridge.Remote",
        side_effect=OSError("Boom"),
    ), patch(
        "homeassistant.components.samsungtv.bridge.SamsungTVWS",
        side_effect=ConnectionFailure("Boom"),
    ):

        # confirm to add the entry
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_SSDP}, data=MOCK_SSDP_DATA
        )
        assert result["type"] == "form"
        assert result["step_id"] == "confirm"

        # device not found
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input="whatever"
        )
        assert result["type"] == "abort"
        assert result["reason"] == RESULT_CANNOT_CONNECT


async def test_ssdp_already_in_progress(hass: HomeAssistant, remote: Mock):
    """Test starting a flow from discovery twice."""

    # confirm to add the entry
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_SSDP}, data=MOCK_SSDP_DATA
    )
    assert result["type"] == "form"
    assert result["step_id"] == "confirm"

    # failed as already in progress
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_SSDP}, data=MOCK_SSDP_DATA
    )
    assert result["type"] == "abort"
    assert result["reason"] == RESULT_ALREADY_IN_PROGRESS


async def test_ssdp_already_configured(hass: HomeAssistant, remote: Mock):
    """Test starting a flow from discovery when already configured."""

    # entry was added
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}, data=MOCK_USER_DATA
    )
    assert result["type"] == "create_entry"
    entry = result["result"]
    assert entry.data[CONF_MANUFACTURER] is None
    assert entry.data[CONF_MODEL] is None
    assert entry.unique_id is None

    # failed as already configured
    result2 = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_SSDP}, data=MOCK_SSDP_DATA
    )
    assert result2["type"] == "abort"
    assert result2["reason"] == RESULT_ALREADY_CONFIGURED

    # check updated device info
    assert entry.unique_id == "0d1cef00-00dc-1000-9c80-4844f7b172de"


async def test_zeroconf(hass: HomeAssistant, remotews: Mock):
    """Test starting a flow from zero."""
    # confirm to add the entry
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=MOCK_ZEROCONF_DATA,
    )
    assert result["type"] == "form"
    assert result["step_id"] == "confirm"

    # entry was added
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input="whatever"
    )
    assert result["type"] == "create_entry"
    assert result["title"] == "Living Room (82GXARRS)"
    assert result["data"][CONF_HOST] == "fake_host"
    assert result["data"][CONF_NAME] == "Living Room"
    assert result["data"][CONF_MAC] == "fake_mac"
    assert result["data"][CONF_MANUFACTURER] == "Samsung"
    assert result["data"][CONF_MODEL] == "82GXARRS"
    assert result["result"].unique_id == "be9554b9-c9fb-41f4-8920-22da015376a4"


async def test_zeroconf_ignores_soundbar(hass: HomeAssistant, remotews_soundbar: Mock):
    """Test starting a flow from zeroconf where the device is actually a soundbar."""
    # confirm to add the entry
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=MOCK_ZEROCONF_DATA,
    )
    assert result["type"] == "abort"
    assert result["reason"] == "not_supported"


async def test_zeroconf_no_device_info(
    hass: HomeAssistant, remotews_no_device_info: Mock
):
    """Test starting a flow from zeroconf where device_info returns None."""
    # confirm to add the entry
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=MOCK_ZEROCONF_DATA,
    )
    assert result["type"] == "abort"
    assert result["reason"] == "not_supported"


async def test_autodetect_websocket(hass: HomeAssistant, remote: Mock, remotews: Mock):
    """Test for send key with autodetection of protocol."""
    with patch(
        "homeassistant.components.samsungtv.bridge.Remote",
        side_effect=OSError("Boom"),
    ), patch(
        "homeassistant.components.samsungtv.config_flow.socket.gethostbyname",
        return_value="fake_host",
    ), patch(
        "homeassistant.components.samsungtv.bridge.SamsungTVWS"
    ) as remotews:
        enter = Mock()
        type(enter).token = PropertyMock(return_value="123456789")
        remote = Mock()
        remote.__enter__ = Mock(return_value=enter)
        remote.__exit__ = Mock(return_value=False)
        remote.rest_device_info.return_value = {
            "id": "uuid:be9554b9-c9fb-41f4-8920-22da015376a4",
            "device": {
                "modelName": "82GXARRS",
                "wifiMac": "aa:bb:cc:dd:ee:ff",
                "udn": "uuid:be9554b9-c9fb-41f4-8920-22da015376a4",
                "mac": "aa:bb:cc:dd:ee:ff",
                "name": "[TV] Living Room",
                "type": "Samsung SmartTV",
            },
        }
        remotews.return_value = remote

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=MOCK_USER_DATA
        )
        assert result["type"] == "create_entry"
        assert result["data"][CONF_METHOD] == "websocket"
        assert result["data"][CONF_TOKEN] == "123456789"
        assert remotews.call_count == 2
        assert remotews.call_args_list == [
            call(**AUTODETECT_WEBSOCKET_SSL),
            call(**DEVICEINFO_WEBSOCKET_SSL),
        ]


async def test_autodetect_auth_missing(hass: HomeAssistant, remote: Mock):
    """Test for send key with autodetection of protocol."""
    with patch(
        "homeassistant.components.samsungtv.bridge.Remote",
        side_effect=[AccessDenied("Boom")],
    ) as remote, patch(
        "homeassistant.components.samsungtv.config_flow.socket.gethostbyname",
        return_value="fake_host",
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=MOCK_USER_DATA
        )
        assert result["type"] == "abort"
        assert result["reason"] == RESULT_AUTH_MISSING
        assert remote.call_count == 1
        assert remote.call_args_list == [call(AUTODETECT_LEGACY)]


async def test_autodetect_not_supported(hass: HomeAssistant, remote: Mock):
    """Test for send key with autodetection of protocol."""
    with patch(
        "homeassistant.components.samsungtv.bridge.Remote",
        side_effect=[UnhandledResponse("Boom")],
    ) as remote, patch(
        "homeassistant.components.samsungtv.config_flow.socket.gethostbyname",
        return_value="fake_host",
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=MOCK_USER_DATA
        )
        assert result["type"] == "abort"
        assert result["reason"] == RESULT_NOT_SUPPORTED
        assert remote.call_count == 1
        assert remote.call_args_list == [call(AUTODETECT_LEGACY)]


async def test_autodetect_legacy(hass: HomeAssistant, remote: Mock):
    """Test for send key with autodetection of protocol."""
    with patch("homeassistant.components.samsungtv.bridge.Remote") as remote:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=MOCK_USER_DATA
        )
        print(result)
        assert result["type"] == "create_entry"
        assert result["data"][CONF_METHOD] == "legacy"
        assert remote.call_count == 1
        assert remote.call_args_list == [call(AUTODETECT_LEGACY)]


async def test_autodetect_none(hass: HomeAssistant, remote: Mock, remotews: Mock):
    """Test for send key with autodetection of protocol."""
    with patch(
        "homeassistant.components.samsungtv.bridge.Remote",
        side_effect=OSError("Boom"),
    ) as remote, patch(
        "homeassistant.components.samsungtv.bridge.SamsungTVWS",
        side_effect=OSError("Boom"),
    ) as remotews, patch(
        "homeassistant.components.samsungtv.config_flow.socket.gethostbyname",
        return_value="fake_host",
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=MOCK_USER_DATA
        )
        assert result["type"] == "abort"
        assert result["reason"] == RESULT_CANNOT_CONNECT
        assert remote.call_count == 1
        assert remote.call_args_list == [
            call(AUTODETECT_LEGACY),
        ]
        assert remotews.call_count == 2
        assert remotews.call_args_list == [
            call(**AUTODETECT_WEBSOCKET_SSL),
            call(**AUTODETECT_WEBSOCKET_PLAIN),
        ]


async def test_update_old_entry(hass: HomeAssistant, remote: Mock):
    """Test update of old entry."""
    with patch("homeassistant.components.samsungtv.bridge.Remote") as remote:
        remote().rest_device_info.return_value = {
            "device": {
                "modelName": "fake_model2",
                "name": "[TV] Fake Name",
                "udn": "uuid:fake_serial",
            }
        }

        entry = MockConfigEntry(domain=DOMAIN, data=MOCK_OLD_ENTRY)
        entry.add_to_hass(hass)

        config_entries_domain = hass.config_entries.async_entries(DOMAIN)
        assert len(config_entries_domain) == 1
        assert entry is config_entries_domain[0]
        assert entry.data[CONF_ID] == "0d1cef00-00dc-1000-9c80-4844f7b172de_old"
        assert entry.data[CONF_IP_ADDRESS] == "fake_ip_old"
        assert not entry.unique_id

        assert await async_setup_component(hass, DOMAIN, {}) is True
        await hass.async_block_till_done()

        # failed as already configured
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_SSDP}, data=MOCK_SSDP_DATA
        )
        assert result["type"] == "abort"
        assert result["reason"] == RESULT_ALREADY_CONFIGURED

        config_entries_domain = hass.config_entries.async_entries(DOMAIN)
        assert len(config_entries_domain) == 1
        entry2 = config_entries_domain[0]

        # check updated device info
        assert entry2.data.get(CONF_ID) is not None
        assert entry2.data.get(CONF_IP_ADDRESS) is not None
        assert entry2.unique_id == "0d1cef00-00dc-1000-9c80-4844f7b172de"
