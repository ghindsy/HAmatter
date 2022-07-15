"""The tests for the Rfxtrx component."""
from __future__ import annotations

from unittest.mock import ANY, call, patch

import RFXtrx as rfxtrxmod

from homeassistant.components.rfxtrx import DOMAIN
from homeassistant.components.rfxtrx.config_flow import (  # noqa: F401 pylint: disable=unused-import
    ConfigFlow,
)
from homeassistant.components.rfxtrx.const import EVENT_RFXTRX_EVENT
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.setup import async_setup_component

from .conftest import create_rfx_test_cfg, setup_rfx_test_cfg
from . import ENTRY_VERSION

from tests.common import MockConfigEntry

SOME_PROTOCOLS = ["ac", "arc"]


async def test_fire_event(hass, rfxtrx):
    """Test fire event."""
    await setup_rfx_test_cfg(
        hass,
        device="/dev/serial/by-id/usb-RFXCOM_RFXtrx433_A1Y0NJGR-if00-port0",
        automatic_add=True,
        devices={
            "0b1100cd0213c7f210010f51": {},
            "0716000100900970": {},
        },
    )

    device_registry: dr.DeviceRegistry = dr.async_get(hass)

    calls = []

    @callback
    def record_event(event):
        """Add recorded event to set."""
        assert event.event_type == "rfxtrx_event"
        calls.append(event.data)

    hass.bus.async_listen(EVENT_RFXTRX_EVENT, record_event)

    await rfxtrx.signal("0b1100cd0213c7f210010f51")
    await rfxtrx.signal("0716000100900970")

    device_id_1 = device_registry.async_get_device(
        identifiers={("rfxtrx", "11_0_213c7f2:16")}
    )
    assert device_id_1

    device_id_2 = device_registry.async_get_device(
        identifiers={("rfxtrx", "16_0_00:90")}
    )
    assert device_id_2

    assert calls == [
        {
            "packet_type": 17,
            "sub_type": 0,
            "type_string": "AC",
            "id_string": "213c7f2:16",
            "data": "0b1100cd0213c7f210010f51",
            "values": {"Command": "On", "Rssi numeric": 5},
            "device_id": device_id_1.id,
        },
        {
            "packet_type": 22,
            "sub_type": 0,
            "type_string": "Byron SX",
            "id_string": "00:90",
            "data": "0716000100900970",
            "values": {"Command": "Sound 9", "Rssi numeric": 7, "Sound": 9},
            "device_id": device_id_2.id,
        },
    ]


async def test_send(hass, rfxtrx):
    """Test configuration."""
    await setup_rfx_test_cfg(hass, device="/dev/null", devices={})

    await hass.services.async_call(
        "rfxtrx", "send", {"event": "0a520802060101ff0f0269"}, blocking=True
    )

    assert rfxtrx.transport.send.mock_calls == [
        call(bytearray(b"\x0a\x52\x08\x02\x06\x01\x01\xff\x0f\x02\x69"))
    ]


async def test_ws_device_remove(hass, hass_ws_client):
    """Test removing a device through device registry."""
    assert await async_setup_component(hass, "config", {})

    device_id = "11_0_213c7f2:16"
    mock_entry = await setup_rfx_test_cfg(
        hass,
        devices={
            "0b1100cd0213c7f210010f51": {"fire_event": True, "device_id": device_id},
        },
    )

    device_reg = dr.async_get(hass)

    device_entry = device_reg.async_get_device(identifiers={("rfxtrx", device_id)})
    assert device_entry

    # Ask to remove existing device
    client = await hass_ws_client(hass)
    await client.send_json(
        {
            "id": 5,
            "type": "config/device_registry/remove_config_entry",
            "config_entry_id": mock_entry.entry_id,
            "device_id": device_entry.id,
        }
    )
    response = await client.receive_json()
    assert response["success"]

    # Verify device entry is removed
    assert device_reg.async_get_device(identifiers={("rfxtrx", device_id)}) is None

    # Verify that the config entry has removed the device
    assert mock_entry.data["devices"] == {}


async def test_connect(hass):
    """Test that we attempt to connect to the device."""
    entry_data = create_rfx_test_cfg(device="/dev/ttyUSBfake")
    mock_entry = MockConfigEntry(
        domain="rfxtrx", unique_id=DOMAIN, data=entry_data, version=ENTRY_VERSION
    )

    mock_entry.add_to_hass(hass)

    with patch.object(rfxtrxmod, "Connect") as connect:
        await hass.config_entries.async_setup(mock_entry.entry_id)
        await hass.async_block_till_done()

    connect.assert_called_once_with("/dev/ttyUSBfake", ANY, modes=ANY)


async def test_connect_with_protocols(hass):
    """Test that we attempt to set protocols."""
    entry_data = create_rfx_test_cfg(device="/dev/ttyUSBfake", protocols=SOME_PROTOCOLS)
    mock_entry = MockConfigEntry(
        domain="rfxtrx", unique_id=DOMAIN, data=entry_data, version=ENTRY_VERSION
    )

    mock_entry.add_to_hass(hass)

    with patch.object(rfxtrxmod, "Connect") as connect:
        await hass.config_entries.async_setup(mock_entry.entry_id)
        await hass.async_block_till_done()

    connect.assert_called_once_with("/dev/ttyUSBfake", ANY, modes=SOME_PROTOCOLS)


async def test_migrate_entry(hass):
    """Test successful migration of entry data."""
    legacy_config = {
        "device": "abcd",
        "host": None,
        "port": None,
        "automatic_add": True,
        "protocols": [],
        "devices": {
            "0b1100cd0213c7f210010f51": {
                "fire_event": True,
                "device_id": ["11", "0", "213c7f2:16"],
            },
            "0716000100900970": {},
        },
    }

    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=DOMAIN, data=legacy_config, version=1
    )
    entry.add_to_hass(hass)

    registry = dr.async_get(hass)
    device_1 = registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={
            (DOMAIN, "11", "0", "213c7f2:16"),
            ("dummy", "id"),
        },
    )
    device_2 = registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={
            (DOMAIN, "16", "0", "00:90"),
        },
    )

    await entry.async_migrate(hass)

    assert dict(entry.data) == {
        "device": "abcd",
        "host": None,
        "port": None,
        "automatic_add": True,
        "protocols": [],
        "devices": {
            "0b1100cd0213c7f210010f51": {
                "fire_event": True,
                "device_id": "11_0_213c7f2:16",
            },
            "0716000100900970": {
                "device_id": "16_0_00:90",
            },
        },
    }
    assert entry.version == 2

    device_1 = registry.async_get(device_1.id)
    assert device_1.identifiers == {
        (DOMAIN, "11_0_213c7f2:16"),
        ("dummy", "id"),
    }

    device_2 = registry.async_get(device_2.id)
    assert device_2.identifiers == {
        (DOMAIN, "16_0_00:90"),
    }
