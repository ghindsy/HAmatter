"""Test ESPHome manager."""
from collections.abc import Awaitable, Callable
from unittest.mock import AsyncMock, call

from aioesphomeapi import (
    APIClient,
    DeviceInfo,
    EntityInfo,
    EntityState,
    UserService,
    UserServiceArg,
    UserServiceArgType,
)
import pytest

from homeassistant import config_entries
from homeassistant.components import dhcp
from homeassistant.components.esphome.const import (
    CONF_DEVICE_NAME,
    DOMAIN,
    STABLE_BLE_VERSION_STR,
)
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component

from .conftest import MockESPHomeDevice

from tests.common import MockConfigEntry


async def test_esphome_device_with_old_bluetooth(
    hass: HomeAssistant,
    mock_client: APIClient,
    mock_esphome_device: Callable[
        [APIClient, list[EntityInfo], list[UserService], list[EntityState]],
        Awaitable[MockESPHomeDevice],
    ],
) -> None:
    """Test a device with old bluetooth creates an issue."""
    entity_info = []
    states = []
    user_service = []
    await mock_esphome_device(
        mock_client=mock_client,
        entity_info=entity_info,
        user_service=user_service,
        states=states,
        device_info={"bluetooth_proxy_feature_flags": 1, "esphome_version": "2023.3.0"},
    )
    await hass.async_block_till_done()
    issue_registry = ir.async_get(hass)
    issue = issue_registry.async_get_issue(
        "esphome", "ble_firmware_outdated-11:22:33:44:55:AA"
    )
    assert (
        issue.learn_more_url
        == f"https://esphome.io/changelog/{STABLE_BLE_VERSION_STR}.html"
    )


async def test_esphome_device_with_password(
    hass: HomeAssistant,
    mock_client: APIClient,
    mock_esphome_device: Callable[
        [APIClient, list[EntityInfo], list[UserService], list[EntityState]],
        Awaitable[MockESPHomeDevice],
    ],
) -> None:
    """Test a device with legacy password creates an issue."""
    entity_info = []
    states = []
    user_service = []

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "test.local",
            CONF_PORT: 6053,
            CONF_PASSWORD: "has",
        },
    )
    entry.add_to_hass(hass)
    await mock_esphome_device(
        mock_client=mock_client,
        entity_info=entity_info,
        user_service=user_service,
        states=states,
        device_info={"bluetooth_proxy_feature_flags": 0, "esphome_version": "2023.3.0"},
        entry=entry,
    )
    await hass.async_block_till_done()
    issue_registry = ir.async_get(hass)
    assert (
        issue_registry.async_get_issue(
            # This issue uses the ESPHome mac address which
            # is always UPPER case
            "esphome",
            "api_password_deprecated-11:22:33:44:55:AA",
        )
        is not None
    )


async def test_esphome_device_with_current_bluetooth(
    hass: HomeAssistant,
    mock_client: APIClient,
    mock_esphome_device: Callable[
        [APIClient, list[EntityInfo], list[UserService], list[EntityState]],
        Awaitable[MockESPHomeDevice],
    ],
) -> None:
    """Test a device with recent bluetooth does not create an issue."""
    entity_info = []
    states = []
    user_service = []
    await mock_esphome_device(
        mock_client=mock_client,
        entity_info=entity_info,
        user_service=user_service,
        states=states,
        device_info={
            "bluetooth_proxy_feature_flags": 1,
            "esphome_version": STABLE_BLE_VERSION_STR,
        },
    )
    await hass.async_block_till_done()
    issue_registry = ir.async_get(hass)
    assert (
        # This issue uses the ESPHome device info mac address which
        # is always UPPER case
        issue_registry.async_get_issue(
            "esphome", "ble_firmware_outdated-11:22:33:44:55:AA"
        )
        is None
    )


async def test_unique_id_updated_to_mac(
    hass: HomeAssistant, mock_client, mock_zeroconf: None
) -> None:
    """Test we update config entry unique ID to MAC address."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "test.local", CONF_PORT: 6053, CONF_PASSWORD: ""},
        unique_id="mock-config-name",
    )
    entry.add_to_hass(hass)

    mock_client.device_info = AsyncMock(
        return_value=DeviceInfo(
            mac_address="1122334455aa",
        )
    )

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.unique_id == "11:22:33:44:55:aa"


async def test_unique_id_not_updated_if_name_same_and_already_mac(
    hass: HomeAssistant, mock_client: APIClient, mock_zeroconf: None
) -> None:
    """Test we never update the entry unique ID event if the name is the same."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "test.local",
            CONF_PORT: 6053,
            CONF_PASSWORD: "",
            CONF_DEVICE_NAME: "test",
        },
        unique_id="11:22:33:44:55:aa",
    )
    entry.add_to_hass(hass)

    mock_client.device_info = AsyncMock(
        return_value=DeviceInfo(mac_address="1122334455ab", name="test")
    )

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Mac should never update
    assert entry.unique_id == "11:22:33:44:55:aa"


async def test_unique_id_updated_if_name_unset_and_already_mac(
    hass: HomeAssistant, mock_client: APIClient, mock_zeroconf: None
) -> None:
    """Test we never update config entry unique ID even if the name is unset."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "test.local", CONF_PORT: 6053, CONF_PASSWORD: ""},
        unique_id="11:22:33:44:55:aa",
    )
    entry.add_to_hass(hass)

    mock_client.device_info = AsyncMock(
        return_value=DeviceInfo(mac_address="1122334455ab", name="test")
    )

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Mac should never update
    assert entry.unique_id == "11:22:33:44:55:aa"


async def test_unique_id_not_updated_if_name_different_and_already_mac(
    hass: HomeAssistant, mock_client: APIClient, mock_zeroconf: None
) -> None:
    """Test we do not update config entry unique ID if the name is different."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "test.local",
            CONF_PORT: 6053,
            CONF_PASSWORD: "",
            CONF_DEVICE_NAME: "test",
        },
        unique_id="11:22:33:44:55:aa",
    )
    entry.add_to_hass(hass)

    mock_client.device_info = AsyncMock(
        return_value=DeviceInfo(mac_address="1122334455ab", name="different")
    )

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Mac should not be updated because name is different
    assert entry.unique_id == "11:22:33:44:55:aa"
    # Name should not be updated either
    assert entry.data[CONF_DEVICE_NAME] == "test"


async def test_name_updated_only_if_mac_matches(
    hass: HomeAssistant, mock_client: APIClient, mock_zeroconf: None
) -> None:
    """Test we update config entry name only if the mac matches."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "test.local",
            CONF_PORT: 6053,
            CONF_PASSWORD: "",
            CONF_DEVICE_NAME: "old",
        },
        unique_id="11:22:33:44:55:aa",
    )
    entry.add_to_hass(hass)

    mock_client.device_info = AsyncMock(
        return_value=DeviceInfo(mac_address="1122334455aa", name="new")
    )

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.unique_id == "11:22:33:44:55:aa"
    assert entry.data[CONF_DEVICE_NAME] == "new"


async def test_name_updated_only_if_mac_was_unset(
    hass: HomeAssistant, mock_client: APIClient, mock_zeroconf: None
) -> None:
    """Test we update config entry name if the old unique id was not a mac."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "test.local",
            CONF_PORT: 6053,
            CONF_PASSWORD: "",
            CONF_DEVICE_NAME: "old",
        },
        unique_id="notamac",
    )
    entry.add_to_hass(hass)

    mock_client.device_info = AsyncMock(
        return_value=DeviceInfo(mac_address="1122334455aa", name="new")
    )

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.unique_id == "11:22:33:44:55:aa"
    assert entry.data[CONF_DEVICE_NAME] == "new"


async def test_connection_aborted_wrong_device(
    hass: HomeAssistant,
    mock_client: APIClient,
    mock_zeroconf: None,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test we abort the connection if the unique id is a mac and neither name or mac match."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "192.168.43.183",
            CONF_PORT: 6053,
            CONF_PASSWORD: "",
            CONF_DEVICE_NAME: "test",
        },
        unique_id="11:22:33:44:55:aa",
    )
    entry.add_to_hass(hass)

    mock_client.device_info = AsyncMock(
        return_value=DeviceInfo(mac_address="1122334455ab", name="different")
    )

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert (
        "Unexpected device found at 192.168.43.183; expected `test` "
        "with mac address `11:22:33:44:55:aa`, found `different` "
        "with mac address `11:22:33:44:55:ab`" in caplog.text
    )

    caplog.clear()
    # Make sure discovery triggers a reconnect to the correct device
    service_info = dhcp.DhcpServiceInfo(
        ip="192.168.43.184",
        hostname="test",
        macaddress="1122334455aa",
    )
    new_info = AsyncMock(
        return_value=DeviceInfo(mac_address="1122334455aa", name="test")
    )
    mock_client.device_info = new_info
    result = await hass.config_entries.flow.async_init(
        "esphome", context={"source": config_entries.SOURCE_DHCP}, data=service_info
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.data[CONF_HOST] == "192.168.43.184"
    await hass.async_block_till_done()
    assert len(new_info.mock_calls) == 1
    assert "Unexpected device found at" not in caplog.text


async def test_debug_logging(
    mock_client: APIClient,
    hass: HomeAssistant,
    mock_generic_device_entry: Callable[
        [APIClient, list[EntityInfo], list[UserService], list[EntityState]],
        Awaitable[MockConfigEntry],
    ],
) -> None:
    """Test enabling and disabling debug logging."""
    assert await async_setup_component(hass, "logger", {"logger": {}})
    await mock_generic_device_entry(
        mock_client=mock_client,
        entity_info=[],
        user_service=[],
        states=[],
    )
    await hass.services.async_call(
        "logger",
        "set_level",
        {"homeassistant.components.esphome": "DEBUG"},
        blocking=True,
    )
    await hass.async_block_till_done()
    mock_client.set_debug.assert_has_calls([call(True)])

    mock_client.reset_mock()
    await hass.services.async_call(
        "logger",
        "set_level",
        {"homeassistant.components.esphome": "WARNING"},
        blocking=True,
    )
    await hass.async_block_till_done()
    mock_client.set_debug.assert_has_calls([call(False)])


async def test_esphome_device_with_dash_in_name_user_services(
    hass: HomeAssistant,
    mock_client: APIClient,
    mock_esphome_device: Callable[
        [APIClient, list[EntityInfo], list[UserService], list[EntityState]],
        Awaitable[MockESPHomeDevice],
    ],
) -> None:
    """Test a device with user services and a dash in the name."""
    entity_info = []
    states = []
    service1 = UserService(
        name="my_service",
        key=1,
        args=[
            UserServiceArg(name="arg1", type=UserServiceArgType.BOOL),
            UserServiceArg(name="arg2", type=UserServiceArgType.INT),
            UserServiceArg(name="arg3", type=UserServiceArgType.FLOAT),
            UserServiceArg(name="arg4", type=UserServiceArgType.STRING),
            UserServiceArg(name="arg5", type=UserServiceArgType.BOOL_ARRAY),
            UserServiceArg(name="arg6", type=UserServiceArgType.INT_ARRAY),
            UserServiceArg(name="arg7", type=UserServiceArgType.FLOAT_ARRAY),
            UserServiceArg(name="arg8", type=UserServiceArgType.STRING_ARRAY),
        ],
    )
    service2 = UserService(
        name="simple_service",
        key=2,
        args=[
            UserServiceArg(name="arg1", type=UserServiceArgType.BOOL),
        ],
    )
    device = await mock_esphome_device(
        mock_client=mock_client,
        entity_info=entity_info,
        user_service=[service1, service2],
        device_info={"name": "with-dash"},
        states=states,
    )
    await hass.async_block_till_done()
    assert hass.services.has_service(DOMAIN, "with_dash_my_service")
    assert hass.services.has_service(DOMAIN, "with_dash_simple_service")

    await hass.services.async_call(DOMAIN, "with_dash_simple_service", {"arg1": True})
    await hass.async_block_till_done()

    mock_client.execute_service.assert_has_calls(
        [
            call(
                UserService(
                    name="simple_service",
                    key=2,
                    args=[UserServiceArg(name="arg1", type=UserServiceArgType.BOOL)],
                ),
                {"arg1": True},
            )
        ]
    )
    mock_client.execute_service.reset_mock()

    # Verify the service can be removed
    mock_client.list_entities_services = AsyncMock(
        return_value=(entity_info, [service1])
    )
    await device.mock_disconnect(True)
    await hass.async_block_till_done()
    await device.mock_connect()
    await hass.async_block_till_done()
    assert hass.services.has_service(DOMAIN, "with_dash_my_service")
    assert not hass.services.has_service(DOMAIN, "with_dash_simple_service")


async def test_esphome_user_services_ignores_invalid_arg_types(
    hass: HomeAssistant,
    mock_client: APIClient,
    mock_esphome_device: Callable[
        [APIClient, list[EntityInfo], list[UserService], list[EntityState]],
        Awaitable[MockESPHomeDevice],
    ],
) -> None:
    """Test a device with user services and a dash in the name."""
    entity_info = []
    states = []
    service1 = UserService(
        name="bad_service",
        key=1,
        args=[
            UserServiceArg(name="arg1", type="wrong"),
        ],
    )
    service2 = UserService(
        name="simple_service",
        key=2,
        args=[
            UserServiceArg(name="arg1", type=UserServiceArgType.BOOL),
        ],
    )
    device = await mock_esphome_device(
        mock_client=mock_client,
        entity_info=entity_info,
        user_service=[service1, service2],
        device_info={"name": "with-dash"},
        states=states,
    )
    await hass.async_block_till_done()
    assert not hass.services.has_service(DOMAIN, "with_dash_bad_service")
    assert hass.services.has_service(DOMAIN, "with_dash_simple_service")

    await hass.services.async_call(DOMAIN, "with_dash_simple_service", {"arg1": True})
    await hass.async_block_till_done()

    mock_client.execute_service.assert_has_calls(
        [
            call(
                UserService(
                    name="simple_service",
                    key=2,
                    args=[UserServiceArg(name="arg1", type=UserServiceArgType.BOOL)],
                ),
                {"arg1": True},
            )
        ]
    )
    mock_client.execute_service.reset_mock()

    # Verify the service can be removed
    mock_client.list_entities_services = AsyncMock(
        return_value=(entity_info, [service2])
    )
    await device.mock_disconnect(True)
    await hass.async_block_till_done()
    await device.mock_connect()
    await hass.async_block_till_done()
    assert hass.services.has_service(DOMAIN, "with_dash_simple_service")
    assert not hass.services.has_service(DOMAIN, "with_dash_bad_service")


async def test_esphome_user_services_changes(
    hass: HomeAssistant,
    mock_client: APIClient,
    mock_esphome_device: Callable[
        [APIClient, list[EntityInfo], list[UserService], list[EntityState]],
        Awaitable[MockESPHomeDevice],
    ],
) -> None:
    """Test a device with user services that change arguments."""
    entity_info = []
    states = []
    service1 = UserService(
        name="simple_service",
        key=2,
        args=[
            UserServiceArg(name="arg1", type=UserServiceArgType.BOOL),
        ],
    )
    device = await mock_esphome_device(
        mock_client=mock_client,
        entity_info=entity_info,
        user_service=[service1],
        device_info={"name": "with-dash"},
        states=states,
    )
    await hass.async_block_till_done()
    assert hass.services.has_service(DOMAIN, "with_dash_simple_service")

    await hass.services.async_call(DOMAIN, "with_dash_simple_service", {"arg1": True})
    await hass.async_block_till_done()

    mock_client.execute_service.assert_has_calls(
        [
            call(
                UserService(
                    name="simple_service",
                    key=2,
                    args=[UserServiceArg(name="arg1", type=UserServiceArgType.BOOL)],
                ),
                {"arg1": True},
            )
        ]
    )
    mock_client.execute_service.reset_mock()

    new_service1 = UserService(
        name="simple_service",
        key=2,
        args=[
            UserServiceArg(name="arg1", type=UserServiceArgType.FLOAT),
        ],
    )

    # Verify the service can be updated
    mock_client.list_entities_services = AsyncMock(
        return_value=(entity_info, [new_service1])
    )
    await device.mock_disconnect(True)
    await hass.async_block_till_done()
    await device.mock_connect()
    await hass.async_block_till_done()
    assert hass.services.has_service(DOMAIN, "with_dash_simple_service")

    await hass.services.async_call(DOMAIN, "with_dash_simple_service", {"arg1": 4.5})
    await hass.async_block_till_done()

    mock_client.execute_service.assert_has_calls(
        [
            call(
                UserService(
                    name="simple_service",
                    key=2,
                    args=[UserServiceArg(name="arg1", type=UserServiceArgType.FLOAT)],
                ),
                {"arg1": 4.5},
            )
        ]
    )
    mock_client.execute_service.reset_mock()
