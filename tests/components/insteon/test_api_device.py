"""Test the device level APIs."""
from unittest.mock import patch

from pyinsteon import pub
from pyinsteon.constants import DeviceAction
from pyinsteon.topics import DEVICE_LIST_CHANGED

from homeassistant.components import insteon
from homeassistant.components.insteon.api import async_load_api
from homeassistant.components.insteon.api.device import (
    DEVICE_ID,
    HA_DEVICE_NOT_FOUND,
    ID,
    INSTEON_DEVICE_NOT_FOUND,
    TYPE,
    async_device_name,
)
from homeassistant.components.insteon.const import DOMAIN, MULTIPLE
from homeassistant.helpers.device_registry import async_get_registry

from .const import MOCK_USER_INPUT_PLM
from .mock_devices import MockDevices

from tests.common import MockConfigEntry


async def _async_setup(hass, hass_ws_client):
    """Set up for tests."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id="abcde12345",
        data=MOCK_USER_INPUT_PLM,
        options={},
    )
    config_entry.add_to_hass(hass)
    async_load_api(hass)

    ws_client = await hass_ws_client(hass)
    devices = MockDevices()
    await devices.async_load()

    dev_reg = await async_get_registry(hass)
    # Create device registry entry for mock node
    ha_device = dev_reg.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, "11.11.11")},
        name="Device 11.11.11",
    )
    return ws_client, devices, ha_device, dev_reg


async def test_get_device_api(hass, hass_ws_client):
    """Test getting an Insteon device."""

    ws_client, devices, ha_device, _ = await _async_setup(hass, hass_ws_client)
    with patch.object(insteon.api.device, "devices", devices):
        await ws_client.send_json(
            {ID: 2, TYPE: "insteon/device/get", DEVICE_ID: ha_device.id}
        )
        msg = await ws_client.receive_json()
        result = msg["result"]

        assert result["name"] == "Device 11.11.11"
        assert result["address"] == "11.11.11"


async def test_no_ha_device(hass, hass_ws_client):
    """Test response when no HA device exists."""

    ws_client, devices, _, _ = await _async_setup(hass, hass_ws_client)
    with patch.object(insteon.api.device, "devices", devices):
        await ws_client.send_json(
            {ID: 2, TYPE: "insteon/device/get", DEVICE_ID: "not_a_device"}
        )
        msg = await ws_client.receive_json()
        assert not msg.get("result")
        assert msg.get("error")
        assert msg["error"]["message"] == HA_DEVICE_NOT_FOUND


async def test_no_insteon_device(hass, hass_ws_client):
    """Test response when no Insteon device exists."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id="abcde12345",
        data=MOCK_USER_INPUT_PLM,
        options={},
    )
    config_entry.add_to_hass(hass)
    async_load_api(hass)

    ws_client = await hass_ws_client(hass)
    devices = MockDevices()
    await devices.async_load()

    dev_reg = await async_get_registry(hass)
    # Create device registry entry for a Insteon device not in the Insteon devices list
    ha_device_1 = dev_reg.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, "AA.BB.CC")},
        name="HA Device Only",
    )
    # Create device registry entry for a non-Insteon device
    ha_device_2 = dev_reg.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={("other_domain", "no address")},
        name="HA Device Only",
    )
    with patch.object(insteon.api.device, "devices", devices):
        await ws_client.send_json(
            {ID: 2, TYPE: "insteon/device/get", DEVICE_ID: ha_device_1.id}
        )
        msg = await ws_client.receive_json()
        assert not msg.get("result")
        assert msg.get("error")
        assert msg["error"]["message"] == INSTEON_DEVICE_NOT_FOUND

        await ws_client.send_json(
            {ID: 3, TYPE: "insteon/device/get", DEVICE_ID: ha_device_2.id}
        )
        msg = await ws_client.receive_json()
        assert not msg.get("result")
        assert msg.get("error")
        assert msg["error"]["message"] == INSTEON_DEVICE_NOT_FOUND


async def test_get_ha_device_name(hass, hass_ws_client):
    """Test getting the HA device name from an Insteon address."""

    _, devices, _, device_reg = await _async_setup(hass, hass_ws_client)

    with patch.object(insteon.api.device, "devices", devices):
        # Test a real HA and Insteon device
        name = await async_device_name(device_reg, "11.11.11")
        assert name == "Device 11.11.11"

        # Test no HA device but a real Insteon device
        name = await async_device_name(device_reg, "22.22.22")
        assert name == "Device 22.22.22 (2)"

        # Test no HA or Insteon device
        name = await async_device_name(device_reg, "BB.BB.BB")
        assert name == ""


async def test_add_device_api(hass, hass_ws_client):
    """Test adding an Insteon device."""

    ws_client, devices, _, _ = await _async_setup(hass, hass_ws_client)
    with patch.object(insteon.api.device, "devices", devices):
        await ws_client.send_json({ID: 2, TYPE: "insteon/device/add", MULTIPLE: False})
        await ws_client.receive_json()
        assert devices.async_add_device_called_with["address"] is None
        assert devices.async_add_device_called_with["multiple"] is False


async def test_notify_on_device_added(hass, hass_ws_client):
    """Test receiving notifications of a new device added."""

    ws_client, devices, _, _ = await _async_setup(hass, hass_ws_client)

    with patch.object(insteon.api.aldb, "devices", devices):
        await ws_client.send_json(
            {
                ID: 2,
                TYPE: "insteon/device/adding",
            }
        )
        msg = await ws_client.receive_json()
        assert msg["success"]

        pub.sendMessage(
            DEVICE_LIST_CHANGED, address="11.22.33", action=DeviceAction.ADDED
        )
        msg = await ws_client.receive_json()
        assert msg["event"]["type"] == "device_added"
        assert msg["event"]["address"] == "11.22.33"

        pub.sendMessage(
            DEVICE_LIST_CHANGED, address=None, action=DeviceAction.COMPLETED
        )
        msg = await ws_client.receive_json()
        assert msg["event"]["type"] == "linking_stopped"


async def test_cancel_add_device(hass, hass_ws_client):
    """Test cancelling adding of a new device."""

    ws_client, devices, _, _ = await _async_setup(hass, hass_ws_client)

    with patch.object(insteon.api.aldb, "devices", devices):
        await ws_client.send_json(
            {
                ID: 2,
                TYPE: "insteon/device/add/cancel",
            }
        )
        msg = await ws_client.receive_json()
        assert msg["success"]
