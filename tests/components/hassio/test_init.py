"""The tests for the hassio component."""
from datetime import timedelta
import os
from unittest.mock import patch

import pytest

from spencerassistant.auth.const import GROUP_ID_ADMIN
from spencerassistant.components import frontend
from spencerassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from spencerassistant.components.hassio import (
    ADDONS_COORDINATOR,
    DOMAIN,
    STORAGE_KEY,
    async_get_addon_store_info,
)
from spencerassistant.components.hassio.handler import HassioAPIError
from spencerassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from spencerassistant.helpers.device_registry import async_get
from spencerassistant.setup import async_setup_component
from spencerassistant.util import dt as dt_util

from tests.common import MockConfigEntry, async_fire_time_changed

MOCK_ENVIRON = {"SUPERVISOR": "127.0.0.1", "SUPERVISOR_TOKEN": "abcdefgh"}


@pytest.fixture()
def extra_os_info():
    """Extra os/info."""
    return {}


@pytest.fixture()
def os_info(extra_os_info):
    """Mock os/info."""
    return {
        "json": {
            "result": "ok",
            "data": {"version_latest": "1.0.0", "version": "1.0.0", **extra_os_info},
        }
    }


@pytest.fixture(autouse=True)
def mock_all(aioclient_mock, request, os_info):
    """Mock all setup requests."""
    aioclient_mock.post("http://127.0.0.1/spencerassistant/options", json={"result": "ok"})
    aioclient_mock.get("http://127.0.0.1/supervisor/ping", json={"result": "ok"})
    aioclient_mock.post("http://127.0.0.1/supervisor/options", json={"result": "ok"})
    aioclient_mock.get(
        "http://127.0.0.1/info",
        json={
            "result": "ok",
            "data": {
                "supervisor": "222",
                "spencerassistant": "0.110.0",
                "hassos": "1.2.3",
            },
        },
    )
    aioclient_mock.get(
        "http://127.0.0.1/store",
        json={
            "result": "ok",
            "data": {"addons": [], "repositories": []},
        },
    )
    aioclient_mock.get(
        "http://127.0.0.1/host/info",
        json={
            "result": "ok",
            "data": {
                "result": "ok",
                "data": {
                    "chassis": "vm",
                    "operating_system": "Debian GNU/Linux 10 (buster)",
                    "kernel": "4.19.0-6-amd64",
                },
            },
        },
    )
    aioclient_mock.get(
        "http://127.0.0.1/core/info",
        json={"result": "ok", "data": {"version_latest": "1.0.0", "version": "1.0.0"}},
    )
    aioclient_mock.get(
        "http://127.0.0.1/os/info",
        **os_info,
    )
    aioclient_mock.get(
        "http://127.0.0.1/supervisor/info",
        json={
            "result": "ok",
            "data": {
                "version_latest": "1.0.0",
                "version": "1.0.0",
                "auto_update": True,
            },
            "addons": [
                {
                    "name": "test",
                    "slug": "test",
                    "installed": True,
                    "update_available": False,
                    "version": "1.0.0",
                    "version_latest": "1.0.0",
                    "repository": "core",
                    "url": "https://github.com/spencer-assistant/addons/test",
                },
                {
                    "name": "test2",
                    "slug": "test2",
                    "installed": True,
                    "update_available": False,
                    "version": "1.0.0",
                    "version_latest": "1.0.0",
                    "repository": "core",
                    "url": "https://github.com",
                },
            ],
        },
    )
    aioclient_mock.get(
        "http://127.0.0.1/addons/test/stats",
        json={
            "result": "ok",
            "data": {
                "cpu_percent": 0.99,
                "memory_usage": 182611968,
                "memory_limit": 3977146368,
                "memory_percent": 4.59,
                "network_rx": 362570232,
                "network_tx": 82374138,
                "blk_read": 46010945536,
                "blk_write": 15051526144,
            },
        },
    )
    aioclient_mock.get(
        "http://127.0.0.1/addons/test2/stats",
        json={
            "result": "ok",
            "data": {
                "cpu_percent": 0.8,
                "memory_usage": 51941376,
                "memory_limit": 3977146368,
                "memory_percent": 1.31,
                "network_rx": 31338284,
                "network_tx": 15692900,
                "blk_read": 740077568,
                "blk_write": 6004736,
            },
        },
    )
    aioclient_mock.get(
        "http://127.0.0.1/addons/test3/stats",
        json={
            "result": "ok",
            "data": {
                "cpu_percent": 0.8,
                "memory_usage": 51941376,
                "memory_limit": 3977146368,
                "memory_percent": 1.31,
                "network_rx": 31338284,
                "network_tx": 15692900,
                "blk_read": 740077568,
                "blk_write": 6004736,
            },
        },
    )
    aioclient_mock.get("http://127.0.0.1/addons/test/changelog", text="")
    aioclient_mock.get(
        "http://127.0.0.1/addons/test/info",
        json={"result": "ok", "data": {"auto_update": True}},
    )
    aioclient_mock.get("http://127.0.0.1/addons/test2/changelog", text="")
    aioclient_mock.get(
        "http://127.0.0.1/addons/test2/info",
        json={"result": "ok", "data": {"auto_update": False}},
    )
    aioclient_mock.get(
        "http://127.0.0.1/ingress/panels", json={"result": "ok", "data": {"panels": {}}}
    )
    aioclient_mock.post("http://127.0.0.1/refresh_updates", json={"result": "ok"})
    aioclient_mock.get(
        "http://127.0.0.1/resolution/info",
        json={
            "result": "ok",
            "data": {
                "unsupported": [],
                "unhealthy": [],
                "suggestions": [],
                "issues": [],
                "checks": [],
            },
        },
    )


async def test_setup_api_ping(hass, aioclient_mock):
    """Test setup with API ping."""
    with patch.dict(os.environ, MOCK_ENVIRON):
        result = await async_setup_component(hass, "hassio", {})
        assert result

    assert aioclient_mock.call_count == 16
    assert hass.components.hassio.get_core_info()["version_latest"] == "1.0.0"
    assert hass.components.hassio.is_hassio()


async def test_setup_api_panel(hass, aioclient_mock):
    """Test setup with API ping."""
    assert await async_setup_component(hass, "frontend", {})
    with patch.dict(os.environ, MOCK_ENVIRON):
        result = await async_setup_component(hass, "hassio", {})
        assert result

    panels = hass.data[frontend.DATA_PANELS]

    assert panels.get("hassio").to_response() == {
        "component_name": "custom",
        "icon": None,
        "title": None,
        "url_path": "hassio",
        "require_admin": True,
        "config": {
            "_panel_custom": {
                "embed_iframe": True,
                "js_url": "/api/hassio/app/entrypoint.js",
                "name": "hassio-main",
                "trust_external": False,
            }
        },
    }


async def test_setup_api_push_api_data(hass, aioclient_mock):
    """Test setup with API push."""
    with patch.dict(os.environ, MOCK_ENVIRON):
        result = await async_setup_component(
            hass, "hassio", {"http": {"server_port": 9999}, "hassio": {}}
        )
        assert result

    assert aioclient_mock.call_count == 16
    assert not aioclient_mock.mock_calls[1][2]["ssl"]
    assert aioclient_mock.mock_calls[1][2]["port"] == 9999
    assert aioclient_mock.mock_calls[1][2]["watchdog"]


async def test_setup_api_push_api_data_server_host(hass, aioclient_mock):
    """Test setup with API push with active server host."""
    with patch.dict(os.environ, MOCK_ENVIRON):
        result = await async_setup_component(
            hass,
            "hassio",
            {"http": {"server_port": 9999, "server_host": "127.0.0.1"}, "hassio": {}},
        )
        assert result

    assert aioclient_mock.call_count == 16
    assert not aioclient_mock.mock_calls[1][2]["ssl"]
    assert aioclient_mock.mock_calls[1][2]["port"] == 9999
    assert not aioclient_mock.mock_calls[1][2]["watchdog"]


async def test_setup_api_push_api_data_default(hass, aioclient_mock, hass_storage):
    """Test setup with API push default data."""
    with patch.dict(os.environ, MOCK_ENVIRON):
        result = await async_setup_component(hass, "hassio", {"http": {}, "hassio": {}})
        assert result

    assert aioclient_mock.call_count == 16
    assert not aioclient_mock.mock_calls[1][2]["ssl"]
    assert aioclient_mock.mock_calls[1][2]["port"] == 8123
    refresh_token = aioclient_mock.mock_calls[1][2]["refresh_token"]
    hassio_user = await hass.auth.async_get_user(
        hass_storage[STORAGE_KEY]["data"]["hassio_user"]
    )
    assert hassio_user is not None
    assert hassio_user.system_generated
    assert len(hassio_user.groups) == 1
    assert hassio_user.groups[0].id == GROUP_ID_ADMIN
    assert hassio_user.name == "Supervisor"
    for token in hassio_user.refresh_tokens.values():
        if token.token == refresh_token:
            break
    else:
        assert False, "refresh token not found"


async def test_setup_adds_admin_group_to_user(hass, aioclient_mock, hass_storage):
    """Test setup with API push default data."""
    # Create user without admin
    user = await hass.auth.async_create_system_user("Hass.io")
    assert not user.is_admin
    await hass.auth.async_create_refresh_token(user)

    hass_storage[STORAGE_KEY] = {
        "data": {"hassio_user": user.id},
        "key": STORAGE_KEY,
        "version": 1,
    }

    with patch.dict(os.environ, MOCK_ENVIRON):
        result = await async_setup_component(hass, "hassio", {"http": {}, "hassio": {}})
        assert result

    assert user.is_admin


async def test_setup_migrate_user_name(hass, aioclient_mock, hass_storage):
    """Test setup with migrating the user name."""
    # Create user with old name
    user = await hass.auth.async_create_system_user("Hass.io")
    await hass.auth.async_create_refresh_token(user)

    hass_storage[STORAGE_KEY] = {
        "data": {"hassio_user": user.id},
        "key": STORAGE_KEY,
        "version": 1,
    }

    with patch.dict(os.environ, MOCK_ENVIRON):
        result = await async_setup_component(hass, "hassio", {"http": {}, "hassio": {}})
        assert result

    assert user.name == "Supervisor"


async def test_setup_api_existing_hassio_user(hass, aioclient_mock, hass_storage):
    """Test setup with API push default data."""
    user = await hass.auth.async_create_system_user("Hass.io test")
    token = await hass.auth.async_create_refresh_token(user)
    hass_storage[STORAGE_KEY] = {"version": 1, "data": {"hassio_user": user.id}}
    with patch.dict(os.environ, MOCK_ENVIRON):
        result = await async_setup_component(hass, "hassio", {"http": {}, "hassio": {}})
        assert result

    assert aioclient_mock.call_count == 16
    assert not aioclient_mock.mock_calls[1][2]["ssl"]
    assert aioclient_mock.mock_calls[1][2]["port"] == 8123
    assert aioclient_mock.mock_calls[1][2]["refresh_token"] == token.token


async def test_setup_core_push_timezone(hass, aioclient_mock):
    """Test setup with API push default data."""
    hass.config.time_zone = "testzone"

    with patch.dict(os.environ, MOCK_ENVIRON):
        result = await async_setup_component(hass, "hassio", {"hassio": {}})
        assert result

    assert aioclient_mock.call_count == 16
    assert aioclient_mock.mock_calls[2][2]["timezone"] == "testzone"

    with patch("spencerassistant.util.dt.set_default_time_zone"):
        await hass.config.async_update(time_zone="America/New_York")
    await hass.async_block_till_done()
    assert aioclient_mock.mock_calls[-1][2]["timezone"] == "America/New_York"


async def test_setup_hassio_no_additional_data(hass, aioclient_mock):
    """Test setup with API push default data."""
    with patch.dict(os.environ, MOCK_ENVIRON), patch.dict(
        os.environ, {"SUPERVISOR_TOKEN": "123456"}
    ):
        result = await async_setup_component(hass, "hassio", {"hassio": {}})
        assert result

    assert aioclient_mock.call_count == 16
    assert aioclient_mock.mock_calls[-1][3]["Authorization"] == "Bearer 123456"


async def test_fail_setup_without_environ_var(hass):
    """Fail setup if no environ variable set."""
    with patch.dict(os.environ, {}, clear=True):
        result = await async_setup_component(hass, "hassio", {})
        assert not result


async def test_warn_when_cannot_connect(hass, caplog):
    """Fail warn when we cannot connect."""
    with patch.dict(os.environ, MOCK_ENVIRON), patch(
        "spencerassistant.components.hassio.HassIO.is_connected",
        return_value=None,
    ):
        result = await async_setup_component(hass, "hassio", {})
        assert result

    assert hass.components.hassio.is_hassio()
    assert "Not connected with the supervisor / system too busy!" in caplog.text


async def test_service_register(hassio_env, hass):
    """Check if service will be setup."""
    assert await async_setup_component(hass, "hassio", {})
    assert hass.services.has_service("hassio", "addon_start")
    assert hass.services.has_service("hassio", "addon_stop")
    assert hass.services.has_service("hassio", "addon_restart")
    assert hass.services.has_service("hassio", "addon_update")
    assert hass.services.has_service("hassio", "addon_stdin")
    assert hass.services.has_service("hassio", "host_shutdown")
    assert hass.services.has_service("hassio", "host_reboot")
    assert hass.services.has_service("hassio", "host_reboot")
    assert hass.services.has_service("hassio", "backup_full")
    assert hass.services.has_service("hassio", "backup_partial")
    assert hass.services.has_service("hassio", "restore_full")
    assert hass.services.has_service("hassio", "restore_partial")


async def test_service_calls(hassio_env, hass, aioclient_mock, caplog):
    """Call service and check the API calls behind that."""
    assert await async_setup_component(hass, "hassio", {})

    aioclient_mock.post("http://127.0.0.1/addons/test/start", json={"result": "ok"})
    aioclient_mock.post("http://127.0.0.1/addons/test/stop", json={"result": "ok"})
    aioclient_mock.post("http://127.0.0.1/addons/test/restart", json={"result": "ok"})
    aioclient_mock.post("http://127.0.0.1/addons/test/update", json={"result": "ok"})
    aioclient_mock.post("http://127.0.0.1/addons/test/stdin", json={"result": "ok"})
    aioclient_mock.post("http://127.0.0.1/host/shutdown", json={"result": "ok"})
    aioclient_mock.post("http://127.0.0.1/host/reboot", json={"result": "ok"})
    aioclient_mock.post("http://127.0.0.1/backups/new/full", json={"result": "ok"})
    aioclient_mock.post("http://127.0.0.1/backups/new/partial", json={"result": "ok"})
    aioclient_mock.post(
        "http://127.0.0.1/backups/test/restore/full", json={"result": "ok"}
    )
    aioclient_mock.post(
        "http://127.0.0.1/backups/test/restore/partial", json={"result": "ok"}
    )

    await hass.services.async_call("hassio", "addon_start", {"addon": "test"})
    await hass.services.async_call("hassio", "addon_stop", {"addon": "test"})
    await hass.services.async_call("hassio", "addon_restart", {"addon": "test"})
    await hass.services.async_call("hassio", "addon_update", {"addon": "test"})
    await hass.services.async_call(
        "hassio", "addon_stdin", {"addon": "test", "input": "test"}
    )
    await hass.async_block_till_done()

    assert aioclient_mock.call_count == 10
    assert aioclient_mock.mock_calls[-1][2] == "test"

    await hass.services.async_call("hassio", "host_shutdown", {})
    await hass.services.async_call("hassio", "host_reboot", {})
    await hass.async_block_till_done()

    assert aioclient_mock.call_count == 12

    await hass.services.async_call("hassio", "backup_full", {})
    await hass.services.async_call(
        "hassio",
        "backup_partial",
        {
            "spencerassistant": True,
            "addons": ["test"],
            "folders": ["ssl"],
            "password": "123456",
        },
    )
    await hass.async_block_till_done()

    assert aioclient_mock.call_count == 14
    assert aioclient_mock.mock_calls[-1][2] == {
        "spencerassistant": True,
        "addons": ["test"],
        "folders": ["ssl"],
        "password": "123456",
    }

    await hass.services.async_call("hassio", "restore_full", {"slug": "test"})
    await hass.async_block_till_done()

    await hass.services.async_call(
        "hassio",
        "restore_partial",
        {
            "slug": "test",
            "spencerassistant": False,
            "addons": ["test"],
            "folders": ["ssl"],
            "password": "123456",
        },
    )
    await hass.async_block_till_done()

    assert aioclient_mock.call_count == 16
    assert aioclient_mock.mock_calls[-1][2] == {
        "addons": ["test"],
        "folders": ["ssl"],
        "spencerassistant": False,
        "password": "123456",
    }


async def test_service_calls_core(hassio_env, hass, aioclient_mock):
    """Call core service and check the API calls behind that."""
    assert await async_setup_component(hass, "hassio", {})

    aioclient_mock.post("http://127.0.0.1/spencerassistant/restart", json={"result": "ok"})
    aioclient_mock.post("http://127.0.0.1/spencerassistant/stop", json={"result": "ok"})

    await hass.services.async_call("spencerassistant", "stop")
    await hass.async_block_till_done()

    assert aioclient_mock.call_count == 6

    await hass.services.async_call("spencerassistant", "check_config")
    await hass.async_block_till_done()

    assert aioclient_mock.call_count == 6

    with patch(
        "spencerassistant.config.async_check_ha_config_file", return_value=None
    ) as mock_check_config:
        await hass.services.async_call("spencerassistant", "restart")
        await hass.async_block_till_done()
        assert mock_check_config.called

    assert aioclient_mock.call_count == 7


async def test_entry_load_and_unload(hass):
    """Test loading and unloading config entry."""
    with patch.dict(os.environ, MOCK_ENVIRON):
        config_entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
        config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    assert SENSOR_DOMAIN in hass.config.components
    assert BINARY_SENSOR_DOMAIN in hass.config.components
    assert ADDONS_COORDINATOR in hass.data

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert ADDONS_COORDINATOR not in hass.data


async def test_migration_off_hassio(hass):
    """Test that when a user moves instance off Hass.io, config entry gets cleaned up."""
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
    config_entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert hass.config_entries.async_entries(DOMAIN) == []


async def test_device_registry_calls(hass):
    """Test device registry entries for hassio."""
    dev_reg = async_get(hass)
    supervisor_mock_data = {
        "version": "1.0.0",
        "version_latest": "1.0.0",
        "auto_update": True,
        "addons": [
            {
                "name": "test",
                "state": "started",
                "slug": "test",
                "installed": True,
                "icon": False,
                "update_available": False,
                "version": "1.0.0",
                "version_latest": "1.0.0",
                "repository": "test",
                "url": "https://github.com/spencer-assistant/addons/test",
            },
            {
                "name": "test2",
                "state": "started",
                "slug": "test2",
                "installed": True,
                "icon": False,
                "update_available": False,
                "version": "1.0.0",
                "version_latest": "1.0.0",
                "url": "https://github.com",
            },
        ],
    }
    os_mock_data = {
        "board": "odroid-n2",
        "boot": "A",
        "update_available": False,
        "version": "5.12",
        "version_latest": "5.12",
    }

    with patch.dict(os.environ, MOCK_ENVIRON), patch(
        "spencerassistant.components.hassio.HassIO.get_supervisor_info",
        return_value=supervisor_mock_data,
    ), patch(
        "spencerassistant.components.hassio.HassIO.get_os_info",
        return_value=os_mock_data,
    ):
        config_entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
        config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        assert len(dev_reg.devices) == 5

    supervisor_mock_data = {
        "version": "1.0.0",
        "version_latest": "1.0.0",
        "auto_update": True,
        "addons": [
            {
                "name": "test2",
                "state": "started",
                "slug": "test2",
                "installed": True,
                "icon": False,
                "update_available": False,
                "version": "1.0.0",
                "version_latest": "1.0.0",
                "url": "https://github.com",
            },
        ],
    }

    # Test that when addon is removed, next update will remove the add-on and subsequent updates won't
    with patch(
        "spencerassistant.components.hassio.HassIO.get_supervisor_info",
        return_value=supervisor_mock_data,
    ), patch(
        "spencerassistant.components.hassio.HassIO.get_os_info",
        return_value=os_mock_data,
    ):
        async_fire_time_changed(hass, dt_util.now() + timedelta(hours=1))
        await hass.async_block_till_done()
        assert len(dev_reg.devices) == 4

        async_fire_time_changed(hass, dt_util.now() + timedelta(hours=2))
        await hass.async_block_till_done()
        assert len(dev_reg.devices) == 4

    supervisor_mock_data = {
        "version": "1.0.0",
        "version_latest": "1.0.0",
        "auto_update": True,
        "addons": [
            {
                "name": "test2",
                "slug": "test2",
                "state": "started",
                "installed": True,
                "icon": False,
                "update_available": False,
                "version": "1.0.0",
                "version_latest": "1.0.0",
                "url": "https://github.com",
            },
            {
                "name": "test3",
                "slug": "test3",
                "state": "stopped",
                "installed": True,
                "icon": False,
                "update_available": False,
                "version": "1.0.0",
                "version_latest": "1.0.0",
                "url": "https://github.com",
            },
        ],
    }

    # Test that when addon is added, next update will reload the entry so we register
    # a new device
    with patch(
        "spencerassistant.components.hassio.HassIO.get_supervisor_info",
        return_value=supervisor_mock_data,
    ), patch(
        "spencerassistant.components.hassio.HassIO.get_os_info",
        return_value=os_mock_data,
    ), patch(
        "spencerassistant.components.hassio.HassIO.get_info",
        return_value={
            "supervisor": "222",
            "spencerassistant": "0.110.0",
            "hassos": None,
        },
    ):
        async_fire_time_changed(hass, dt_util.now() + timedelta(hours=3))
        await hass.async_block_till_done()
        assert len(dev_reg.devices) == 4


async def test_coordinator_updates(hass, caplog):
    """Test coordinator updates."""
    await async_setup_component(hass, "spencerassistant", {})
    with patch.dict(os.environ, MOCK_ENVIRON), patch(
        "spencerassistant.components.hassio.HassIO.refresh_updates"
    ) as refresh_updates_mock:
        config_entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
        config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        assert refresh_updates_mock.call_count == 1

    with patch(
        "spencerassistant.components.hassio.HassIO.refresh_updates",
    ) as refresh_updates_mock:
        async_fire_time_changed(hass, dt_util.now() + timedelta(minutes=20))
        await hass.async_block_till_done()
        assert refresh_updates_mock.call_count == 0

    with patch(
        "spencerassistant.components.hassio.HassIO.refresh_updates",
    ) as refresh_updates_mock:
        await hass.services.async_call(
            "spencerassistant",
            "update_entity",
            {
                "entity_id": [
                    "update.spencer_assistant_core_update",
                    "update.spencer_assistant_supervisor_update",
                ]
            },
            blocking=True,
        )
        assert refresh_updates_mock.call_count == 1

    # There is a 10s cooldown on the debouncer
    async_fire_time_changed(hass, dt_util.now() + timedelta(seconds=10))
    await hass.async_block_till_done()

    with patch(
        "spencerassistant.components.hassio.HassIO.refresh_updates",
        side_effect=HassioAPIError("Unknown"),
    ) as refresh_updates_mock:
        await hass.services.async_call(
            "spencerassistant",
            "update_entity",
            {
                "entity_id": [
                    "update.spencer_assistant_core_update",
                    "update.spencer_assistant_supervisor_update",
                ]
            },
            blocking=True,
        )
        assert refresh_updates_mock.call_count == 1
        assert "Error on Supervisor API: Unknown" in caplog.text


@pytest.mark.parametrize(
    "extra_os_info, integration",
    [
        ({"board": "odroid-c2"}, "hardkernel"),
        ({"board": "odroid-c4"}, "hardkernel"),
        ({"board": "odroid-n2"}, "hardkernel"),
        ({"board": "odroid-xu4"}, "hardkernel"),
        ({"board": "rpi2"}, "raspberry_pi"),
        ({"board": "rpi3"}, "raspberry_pi"),
        ({"board": "rpi3-64"}, "raspberry_pi"),
        ({"board": "rpi4"}, "raspberry_pi"),
        ({"board": "rpi4-64"}, "raspberry_pi"),
        ({"board": "yellow"}, "spencerassistant_yellow"),
    ],
)
async def test_setup_hardware_integration(hass, aioclient_mock, integration):
    """Test setup initiates hardware integration."""

    with patch.dict(os.environ, MOCK_ENVIRON), patch(
        f"spencerassistant.components.{integration}.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await async_setup_component(hass, "hassio", {"hassio": {}})
        assert result
        await hass.async_block_till_done()

    assert aioclient_mock.call_count == 16
    assert len(mock_setup_entry.mock_calls) == 1


async def test_get_store_addon_info(hass, hassio_stubs, aioclient_mock):
    """Test get store add-on info from Supervisor API."""
    aioclient_mock.clear_requests()
    aioclient_mock.get(
        "http://127.0.0.1/store/addons/test",
        json={"result": "ok", "data": {"name": "bla"}},
    )

    data = await async_get_addon_store_info(hass, "test")
    assert data["name"] == "bla"
    assert aioclient_mock.call_count == 1
