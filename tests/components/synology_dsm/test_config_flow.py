"""Tests for the Synology DSM config flow."""
import pytest
from synology_dsm.exceptions import (
    SynologyDSMException,
    SynologyDSMLogin2SAFailedException,
    SynologyDSMLogin2SARequiredException,
    SynologyDSMLoginInvalidException,
    SynologyDSMRequestException,
)

from homeassistant import data_entry_flow, setup
from homeassistant.components import ssdp
from homeassistant.components.synology_dsm.config_flow import CONF_OTP_CODE
from homeassistant.components.synology_dsm.const import (
    CONF_FILTER_STORAGE,
    CONF_VOLUMES,
    DEFAULT_PORT,
    DEFAULT_PORT_SSL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DEFAULT_USE_SSL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
)
from homeassistant.config_entries import SOURCE_SSDP, SOURCE_USER
from homeassistant.const import (
    CONF_DISKS,
    CONF_HOST,
    CONF_MAC,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_SSL,
    CONF_TIMEOUT,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.helpers.typing import HomeAssistantType

from .consts import (
    DEVICE_TOKEN,
    HOST,
    MACS,
    PASSWORD,
    PORT,
    SERIAL,
    SERIAL_2,
    USE_SSL,
    USERNAME,
    VERIFY_SSL,
)

from tests.async_mock import MagicMock, Mock, patch
from tests.common import MockConfigEntry

DISKS = ["sda", "sdb", "sdc"]
VOLUMES = ["volume_1"]


@pytest.fixture(name="service")
def mock_controller_service():
    """Mock a successful service."""
    with patch(
        "homeassistant.components.synology_dsm.config_flow.SynologyDSM"
    ) as service_mock:
        service_mock.return_value.information.serial = SERIAL
        service_mock.return_value.utilisation.cpu_user_load = 1
        service_mock.return_value.storage.disks_ids = DISKS
        service_mock.return_value.storage.volumes_ids = VOLUMES
        service_mock.return_value.network.macs = MACS
        yield service_mock


@pytest.fixture(name="service_2sa")
def mock_controller_service_2sa():
    """Mock a successful service with 2SA login."""
    with patch(
        "homeassistant.components.synology_dsm.config_flow.SynologyDSM"
    ) as service_mock:
        service_mock.return_value.login = Mock(
            side_effect=SynologyDSMLogin2SARequiredException(USERNAME)
        )
        service_mock.return_value.information.serial = SERIAL
        service_mock.return_value.utilisation.cpu_user_load = 1
        service_mock.return_value.storage.disks_ids = DISKS
        service_mock.return_value.storage.volumes_ids = VOLUMES
        service_mock.return_value.network.macs = MACS
        yield service_mock


@pytest.fixture(name="service_vdsm")
def mock_controller_service_vdsm():
    """Mock a successful service."""
    with patch(
        "homeassistant.components.synology_dsm.config_flow.SynologyDSM"
    ) as service_mock:
        service_mock.return_value.information.serial = SERIAL
        service_mock.return_value.utilisation.cpu_user_load = 1
        service_mock.return_value.storage.disks_ids = []
        service_mock.return_value.storage.volumes_ids = VOLUMES
        service_mock.return_value.network.macs = MACS
        yield service_mock


@pytest.fixture(name="service_failed")
def mock_controller_service_failed():
    """Mock a failed service."""
    with patch(
        "homeassistant.components.synology_dsm.config_flow.SynologyDSM"
    ) as service_mock:
        service_mock.return_value.information.serial = None
        service_mock.return_value.utilisation.cpu_user_load = None
        service_mock.return_value.storage.disks_ids = []
        service_mock.return_value.storage.volumes_ids = []
        service_mock.return_value.network.macs = []
        yield service_mock


async def test_user(hass: HomeAssistantType, service: MagicMock):
    """Test user config."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=None
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "user"

    # test with all provided
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={
            CONF_HOST: HOST,
            CONF_PORT: PORT,
            CONF_SSL: USE_SSL,
            CONF_VERIFY_SSL: VERIFY_SSL,
            CONF_USERNAME: USERNAME,
            CONF_PASSWORD: PASSWORD,
        },
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result["result"].unique_id == SERIAL
    assert result["title"] == HOST
    assert result["data"][CONF_HOST] == HOST
    assert result["data"][CONF_PORT] == PORT
    assert result["data"][CONF_SSL] == USE_SSL
    assert result["data"][CONF_VERIFY_SSL] == VERIFY_SSL
    assert result["data"][CONF_USERNAME] == USERNAME
    assert result["data"][CONF_PASSWORD] == PASSWORD
    assert result["data"][CONF_MAC] == MACS
    assert result["data"].get("device_token") is None
    assert result["data"].get(CONF_DISKS) is None
    assert result["data"].get(CONF_VOLUMES) is None

    service.return_value.information.serial = SERIAL_2
    # test without port + False SSL
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={
            CONF_HOST: HOST,
            CONF_SSL: False,
            CONF_VERIFY_SSL: VERIFY_SSL,
            CONF_USERNAME: USERNAME,
            CONF_PASSWORD: PASSWORD,
        },
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result["result"].unique_id == SERIAL_2
    assert result["title"] == HOST
    assert result["data"][CONF_HOST] == HOST
    assert result["data"][CONF_PORT] == DEFAULT_PORT
    assert not result["data"][CONF_SSL]
    assert result["data"][CONF_VERIFY_SSL] == VERIFY_SSL
    assert result["data"][CONF_USERNAME] == USERNAME
    assert result["data"][CONF_PASSWORD] == PASSWORD
    assert result["data"][CONF_MAC] == MACS
    assert result["data"].get("device_token") is None
    assert result["data"].get(CONF_DISKS) is None
    assert result["data"].get(CONF_VOLUMES) is None


async def test_user_filter_storage(hass: HomeAssistantType, service: MagicMock):
    """Test user config with filter for disks and volumes."""
    # test with filter storage enabled
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={
            CONF_HOST: HOST,
            CONF_PORT: PORT,
            CONF_SSL: USE_SSL,
            CONF_VERIFY_SSL: VERIFY_SSL,
            CONF_USERNAME: USERNAME,
            CONF_PASSWORD: PASSWORD,
            CONF_FILTER_STORAGE: True,
        },
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "filter_storage"

    # test with filter storage enabled and selection is done
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={
            CONF_HOST: HOST,
            CONF_PORT: PORT,
            CONF_SSL: USE_SSL,
            CONF_VERIFY_SSL: VERIFY_SSL,
            CONF_USERNAME: USERNAME,
            CONF_PASSWORD: PASSWORD,
            CONF_FILTER_STORAGE: True,
            CONF_DISKS: DISKS,
            CONF_VOLUMES: VOLUMES,
        },
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result["data"][CONF_DISKS] == DISKS
    assert result["data"][CONF_VOLUMES] == VOLUMES


async def test_user_2sa(hass: HomeAssistantType, service_2sa: MagicMock):
    """Test user with 2sa authentication config."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={CONF_HOST: HOST, CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "2sa"

    # Failed the first time because was too slow to enter the code
    service_2sa.return_value.login = Mock(
        side_effect=SynologyDSMLogin2SAFailedException
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_OTP_CODE: "000000"}
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "2sa"
    assert result["errors"] == {CONF_OTP_CODE: "otp_failed"}

    # Successful login with 2SA code
    service_2sa.return_value.login = Mock(return_value=True)
    service_2sa.return_value.device_token = DEVICE_TOKEN
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_OTP_CODE: "123456"}
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result["result"].unique_id == SERIAL
    assert result["title"] == HOST
    assert result["data"][CONF_HOST] == HOST
    assert result["data"][CONF_PORT] == DEFAULT_PORT_SSL
    assert result["data"][CONF_SSL] == DEFAULT_USE_SSL
    assert result["data"][CONF_VERIFY_SSL] == DEFAULT_VERIFY_SSL
    assert result["data"][CONF_USERNAME] == USERNAME
    assert result["data"][CONF_PASSWORD] == PASSWORD
    assert result["data"][CONF_MAC] == MACS
    assert result["data"].get("device_token") == DEVICE_TOKEN
    assert result["data"].get(CONF_DISKS) is None
    assert result["data"].get(CONF_VOLUMES) is None


async def test_user_vdsm(hass: HomeAssistantType, service_vdsm: MagicMock):
    """Test user config."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=None
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "user"

    # test with all provided
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={
            CONF_HOST: HOST,
            CONF_PORT: PORT,
            CONF_SSL: USE_SSL,
            CONF_VERIFY_SSL: VERIFY_SSL,
            CONF_USERNAME: USERNAME,
            CONF_PASSWORD: PASSWORD,
        },
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result["result"].unique_id == SERIAL
    assert result["title"] == HOST
    assert result["data"][CONF_HOST] == HOST
    assert result["data"][CONF_PORT] == PORT
    assert result["data"][CONF_SSL] == USE_SSL
    assert result["data"][CONF_VERIFY_SSL] == VERIFY_SSL
    assert result["data"][CONF_USERNAME] == USERNAME
    assert result["data"][CONF_PASSWORD] == PASSWORD
    assert result["data"][CONF_MAC] == MACS
    assert result["data"].get("device_token") is None
    assert result["data"].get(CONF_DISKS) is None
    assert result["data"].get(CONF_VOLUMES) is None


async def test_abort_if_already_setup(hass: HomeAssistantType, service: MagicMock):
    """Test we abort if the account is already setup."""
    MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: HOST, CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
        unique_id=SERIAL,
    ).add_to_hass(hass)

    # Should fail, same HOST:PORT
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={CONF_HOST: HOST, CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT
    assert result["reason"] == "already_configured"


async def test_login_failed(hass: HomeAssistantType, service: MagicMock):
    """Test when we have errors during login."""
    service.return_value.login = Mock(
        side_effect=(SynologyDSMLoginInvalidException(USERNAME))
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={CONF_HOST: HOST, CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["errors"] == {CONF_USERNAME: "invalid_auth"}


async def test_connection_failed(hass: HomeAssistantType, service: MagicMock):
    """Test when we have errors during connection."""
    service.return_value.login = Mock(
        side_effect=SynologyDSMRequestException(IOError("arg"))
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={CONF_HOST: HOST, CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["errors"] == {CONF_HOST: "cannot_connect"}


async def test_unknown_failed(hass: HomeAssistantType, service: MagicMock):
    """Test when we have an unknown error."""
    service.return_value.login = Mock(side_effect=SynologyDSMException(None, None))

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={CONF_HOST: HOST, CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["errors"] == {"base": "unknown"}


async def test_missing_data_after_login(
    hass: HomeAssistantType, service_failed: MagicMock
):
    """Test when we have errors during connection."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={CONF_HOST: HOST, CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["errors"] == {"base": "missing_data"}


async def test_form_ssdp_already_configured(
    hass: HomeAssistantType, service: MagicMock
):
    """Test ssdp abort when the serial number is already configured."""
    await setup.async_setup_component(hass, "persistent_notification", {})

    MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: HOST,
            CONF_USERNAME: USERNAME,
            CONF_PASSWORD: PASSWORD,
            CONF_MAC: MACS,
        },
        unique_id=SERIAL,
    ).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_SSDP},
        data={
            ssdp.ATTR_SSDP_LOCATION: "http://192.168.1.5:5000",
            ssdp.ATTR_UPNP_FRIENDLY_NAME: "mydsm",
            ssdp.ATTR_UPNP_SERIAL: "001132XXXX59",  # Existing in MACS[0], but SSDP does not have `-`
        },
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT


async def test_form_ssdp(hass: HomeAssistantType, service: MagicMock):
    """Test we can setup from ssdp."""
    await setup.async_setup_component(hass, "persistent_notification", {})

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_SSDP},
        data={
            ssdp.ATTR_SSDP_LOCATION: "http://192.168.1.5:5000",
            ssdp.ATTR_UPNP_FRIENDLY_NAME: "mydsm",
            ssdp.ATTR_UPNP_SERIAL: "001132XXXX99",  # MAC address, but SSDP does not have `-`
        },
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "link"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD}
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result["result"].unique_id == SERIAL
    assert result["title"] == "192.168.1.5"
    assert result["data"][CONF_HOST] == "192.168.1.5"
    assert result["data"][CONF_PORT] == 5001
    assert result["data"][CONF_SSL] == DEFAULT_USE_SSL
    assert result["data"][CONF_VERIFY_SSL] == DEFAULT_VERIFY_SSL
    assert result["data"][CONF_USERNAME] == USERNAME
    assert result["data"][CONF_PASSWORD] == PASSWORD
    assert result["data"][CONF_MAC] == MACS
    assert result["data"].get("device_token") is None
    assert result["data"].get(CONF_DISKS) is None
    assert result["data"].get(CONF_VOLUMES) is None


async def test_options_flow(hass: HomeAssistantType, service: MagicMock):
    """Test config flow options."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: HOST,
            CONF_USERNAME: USERNAME,
            CONF_PASSWORD: PASSWORD,
            CONF_MAC: MACS,
        },
        unique_id=SERIAL,
    )
    config_entry.add_to_hass(hass)

    assert config_entry.options == {}

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "init"

    # Scan interval
    # Default
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={},
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert config_entry.options[CONF_SCAN_INTERVAL] == DEFAULT_SCAN_INTERVAL
    assert config_entry.options[CONF_TIMEOUT] == DEFAULT_TIMEOUT

    # Manual
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_SCAN_INTERVAL: 2, CONF_TIMEOUT: 30},
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert config_entry.options[CONF_SCAN_INTERVAL] == 2
    assert config_entry.options[CONF_TIMEOUT] == 30
