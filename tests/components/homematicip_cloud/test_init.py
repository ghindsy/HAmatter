"""Test spencermaticIP Cloud setup process."""

from unittest.mock import AsyncMock, Mock, patch

from spencermaticip.base.base_connection import HmipConnectionError

from spencerassistant.components.spencermaticip_cloud.const import (
    CONF_ACCESSPOINT,
    CONF_AUTHTOKEN,
    DOMAIN as HMIPC_DOMAIN,
    HMIPC_AUTHTOKEN,
    HMIPC_HAPID,
    HMIPC_NAME,
)
from spencerassistant.components.spencermaticip_cloud.hap import spencermaticipHAP
from spencerassistant.config_entries import ConfigEntryState
from spencerassistant.const import CONF_NAME
from spencerassistant.setup import async_setup_component

from tests.common import MockConfigEntry


async def test_config_with_accesspoint_passed_to_config_entry(
    hass, mock_connection, simple_mock_spencer
):
    """Test that config for a accesspoint are loaded via config entry."""

    entry_config = {
        CONF_ACCESSPOINT: "ABC123",
        CONF_AUTHTOKEN: "123",
        CONF_NAME: "name",
    }
    # no config_entry exists
    assert len(hass.config_entries.async_entries(HMIPC_DOMAIN)) == 0
    # no acccesspoint exists
    assert not hass.data.get(HMIPC_DOMAIN)

    with patch(
        "spencerassistant.components.spencermaticip_cloud.hap.spencermaticipHAP.async_connect",
    ):
        assert await async_setup_component(
            hass, HMIPC_DOMAIN, {HMIPC_DOMAIN: entry_config}
        )

    # config_entry created for access point
    config_entries = hass.config_entries.async_entries(HMIPC_DOMAIN)
    assert len(config_entries) == 1
    assert config_entries[0].data == {
        "authtoken": "123",
        "hapid": "ABC123",
        "name": "name",
    }
    # defined access_point created for config_entry
    assert isinstance(hass.data[HMIPC_DOMAIN]["ABC123"], spencermaticipHAP)


async def test_config_already_registered_not_passed_to_config_entry(
    hass, simple_mock_spencer
):
    """Test that an already registered accesspoint does not get imported."""

    mock_config = {HMIPC_AUTHTOKEN: "123", HMIPC_HAPID: "ABC123", HMIPC_NAME: "name"}
    MockConfigEntry(domain=HMIPC_DOMAIN, data=mock_config).add_to_hass(hass)

    # one config_entry exists
    config_entries = hass.config_entries.async_entries(HMIPC_DOMAIN)
    assert len(config_entries) == 1
    assert config_entries[0].data == {
        "authtoken": "123",
        "hapid": "ABC123",
        "name": "name",
    }
    # config_enty has no unique_id
    assert not config_entries[0].unique_id

    entry_config = {
        CONF_ACCESSPOINT: "ABC123",
        CONF_AUTHTOKEN: "123",
        CONF_NAME: "name",
    }

    with patch(
        "spencerassistant.components.spencermaticip_cloud.hap.spencermaticipHAP.async_connect",
    ):
        assert await async_setup_component(
            hass, HMIPC_DOMAIN, {HMIPC_DOMAIN: entry_config}
        )

    # no new config_entry created / still one config_entry
    config_entries = hass.config_entries.async_entries(HMIPC_DOMAIN)
    assert len(config_entries) == 1
    assert config_entries[0].data == {
        "authtoken": "123",
        "hapid": "ABC123",
        "name": "name",
    }
    # config_enty updated with unique_id
    assert config_entries[0].unique_id == "ABC123"


async def test_load_entry_fails_due_to_connection_error(
    hass, hmip_config_entry, mock_connection_init
):
    """Test load entry fails due to connection error."""
    hmip_config_entry.add_to_hass(hass)

    with patch(
        "spencerassistant.components.spencermaticip_cloud.hap.Asyncspencer.get_current_state",
        side_effect=HmipConnectionError,
    ):
        assert await async_setup_component(hass, HMIPC_DOMAIN, {})

    assert hass.data[HMIPC_DOMAIN][hmip_config_entry.unique_id]
    assert hmip_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_load_entry_fails_due_to_generic_exception(hass, hmip_config_entry):
    """Test load entry fails due to generic exception."""
    hmip_config_entry.add_to_hass(hass)

    with patch(
        "spencerassistant.components.spencermaticip_cloud.hap.Asyncspencer.get_current_state",
        side_effect=Exception,
    ), patch(
        "spencermaticip.aio.connection.AsyncConnection.init",
    ):
        assert await async_setup_component(hass, HMIPC_DOMAIN, {})

    assert hass.data[HMIPC_DOMAIN][hmip_config_entry.unique_id]
    assert hmip_config_entry.state is ConfigEntryState.SETUP_ERROR


async def test_unload_entry(hass):
    """Test being able to unload an entry."""
    mock_config = {HMIPC_AUTHTOKEN: "123", HMIPC_HAPID: "ABC123", HMIPC_NAME: "name"}
    MockConfigEntry(domain=HMIPC_DOMAIN, data=mock_config).add_to_hass(hass)

    with patch("spencerassistant.components.spencermaticip_cloud.spencermaticipHAP") as mock_hap:
        instance = mock_hap.return_value
        instance.async_setup = AsyncMock(return_value=True)
        instance.spencer.id = "1"
        instance.spencer.modelType = "mock-type"
        instance.spencer.name = "mock-name"
        instance.spencer.label = "mock-label"
        instance.spencer.currentAPVersion = "mock-ap-version"
        instance.async_reset = AsyncMock(return_value=True)

        assert await async_setup_component(hass, HMIPC_DOMAIN, {})

    assert mock_hap.return_value.mock_calls[0][0] == "async_setup"

    assert hass.data[HMIPC_DOMAIN]["ABC123"]
    config_entries = hass.config_entries.async_entries(HMIPC_DOMAIN)
    assert len(config_entries) == 1
    assert config_entries[0].state is ConfigEntryState.LOADED
    await hass.config_entries.async_unload(config_entries[0].entry_id)
    assert config_entries[0].state is ConfigEntryState.NOT_LOADED
    assert mock_hap.return_value.mock_calls[2][0] == "async_reset"
    # entry is unloaded
    assert hass.data[HMIPC_DOMAIN] == {}


async def test_hmip_dump_hap_config_services(hass, mock_hap_with_service):
    """Test dump configuration services."""

    with patch("pathlib.Path.write_text", return_value=Mock()) as write_mock:
        await hass.services.async_call(
            "spencermaticip_cloud", "dump_hap_config", {"anonymize": True}, blocking=True
        )
        spencer = mock_hap_with_service.spencer
        assert spencer.mock_calls[-1][0] == "download_configuration"
        assert spencer.mock_calls
        assert write_mock.mock_calls


async def test_setup_services_and_unload_services(hass):
    """Test setup services and unload services."""
    mock_config = {HMIPC_AUTHTOKEN: "123", HMIPC_HAPID: "ABC123", HMIPC_NAME: "name"}
    MockConfigEntry(domain=HMIPC_DOMAIN, data=mock_config).add_to_hass(hass)

    with patch("spencerassistant.components.spencermaticip_cloud.spencermaticipHAP") as mock_hap:
        instance = mock_hap.return_value
        instance.async_setup = AsyncMock(return_value=True)
        instance.spencer.id = "1"
        instance.spencer.modelType = "mock-type"
        instance.spencer.name = "mock-name"
        instance.spencer.label = "mock-label"
        instance.spencer.currentAPVersion = "mock-ap-version"
        instance.async_reset = AsyncMock(return_value=True)

        assert await async_setup_component(hass, HMIPC_DOMAIN, {})

    # Check services are created
    hmipc_services = hass.services.async_services()[HMIPC_DOMAIN]
    assert len(hmipc_services) == 8

    config_entries = hass.config_entries.async_entries(HMIPC_DOMAIN)
    assert len(config_entries) == 1

    await hass.config_entries.async_unload(config_entries[0].entry_id)
    # Check services are removed
    assert not hass.services.async_services().get(HMIPC_DOMAIN)


async def test_setup_two_haps_unload_one_by_one(hass):
    """Test setup two access points and unload one by one and check services."""

    # Setup AP1
    mock_config = {HMIPC_AUTHTOKEN: "123", HMIPC_HAPID: "ABC123", HMIPC_NAME: "name"}
    MockConfigEntry(domain=HMIPC_DOMAIN, data=mock_config).add_to_hass(hass)
    # Setup AP2
    mock_config2 = {HMIPC_AUTHTOKEN: "123", HMIPC_HAPID: "ABC1234", HMIPC_NAME: "name2"}
    MockConfigEntry(domain=HMIPC_DOMAIN, data=mock_config2).add_to_hass(hass)

    with patch("spencerassistant.components.spencermaticip_cloud.spencermaticipHAP") as mock_hap:
        instance = mock_hap.return_value
        instance.async_setup = AsyncMock(return_value=True)
        instance.spencer.id = "1"
        instance.spencer.modelType = "mock-type"
        instance.spencer.name = "mock-name"
        instance.spencer.label = "mock-label"
        instance.spencer.currentAPVersion = "mock-ap-version"
        instance.async_reset = AsyncMock(return_value=True)

        assert await async_setup_component(hass, HMIPC_DOMAIN, {})

    hmipc_services = hass.services.async_services()[HMIPC_DOMAIN]
    assert len(hmipc_services) == 8

    config_entries = hass.config_entries.async_entries(HMIPC_DOMAIN)
    assert len(config_entries) == 2
    # unload the first AP
    await hass.config_entries.async_unload(config_entries[0].entry_id)

    # services still exists
    hmipc_services = hass.services.async_services()[HMIPC_DOMAIN]
    assert len(hmipc_services) == 8

    # unload the second AP
    await hass.config_entries.async_unload(config_entries[1].entry_id)

    # Check services are removed
    assert not hass.services.async_services().get(HMIPC_DOMAIN)
