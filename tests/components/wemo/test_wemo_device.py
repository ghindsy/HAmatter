"""Tests for wemo_device.py."""
import asyncio
from unittest.mock import patch

import async_timeout
import pytest
from pywemo.exceptions import ActionException, PyWeMoException
from pywemo.subscribe import EVENT_TYPE_LONG_PRESS

from homeassistant import runner
from homeassistant.components.wemo import CONF_DISCOVERY, CONF_STATIC, wemo_device
from homeassistant.components.wemo.const import DOMAIN, WEMO_SUBSCRIPTION_EVENT
from homeassistant.core import callback
from homeassistant.helpers import device_registry
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.setup import async_setup_component

from .conftest import MOCK_HOST

asyncio.set_event_loop_policy(runner.HassEventLoopPolicy(True))


@pytest.fixture
def pywemo_model():
    """Pywemo Dimmer models use the light platform (WemoDimmer class)."""
    return "Dimmer"


async def test_async_register_device_longpress_fails(hass, pywemo_device):
    """Device is still registered if ensure_long_press_virtual_device fails."""
    with patch.object(pywemo_device, "ensure_long_press_virtual_device") as elp:
        elp.side_effect = PyWeMoException
        assert await async_setup_component(
            hass,
            DOMAIN,
            {
                DOMAIN: {
                    CONF_DISCOVERY: False,
                    CONF_STATIC: [MOCK_HOST],
                },
            },
        )
        await hass.async_block_till_done()
    dr = device_registry.async_get(hass)
    device_entries = list(dr.devices.values())
    assert len(device_entries) == 1
    device_wrapper = wemo_device.async_get_device(hass, device_entries[0].id)
    assert device_wrapper.supports_long_press is False


async def test_long_press_event(hass, pywemo_registry, wemo_entity):
    """Device fires a long press event."""
    device_wrapper = wemo_device.async_get_device(hass, wemo_entity.device_id)
    got_event = asyncio.Event()
    event_data = {}

    @callback
    def async_event_received(event):
        nonlocal event_data
        event_data = event.data
        got_event.set()

    hass.bus.async_listen_once(WEMO_SUBSCRIPTION_EVENT, async_event_received)

    await hass.async_add_executor_job(
        pywemo_registry.callbacks[device_wrapper.wemo.name],
        device_wrapper.wemo,
        EVENT_TYPE_LONG_PRESS,
        "testing_params",
    )

    async with async_timeout.timeout(8):
        await got_event.wait()

    assert event_data == {
        "device_id": wemo_entity.device_id,
        "name": device_wrapper.wemo.name,
        "params": "testing_params",
        "type": EVENT_TYPE_LONG_PRESS,
        "unique_id": device_wrapper.wemo.serialnumber,
    }


async def test_subscription_callback(hass, pywemo_registry, wemo_entity):
    """Device processes a registry subscription callback."""
    device_wrapper = wemo_device.async_get_device(hass, wemo_entity.device_id)
    device_wrapper.coordinator.last_update_success = False

    got_callback = asyncio.Event()

    @callback
    def async_received_callback():
        got_callback.set()

    device_wrapper.coordinator.async_add_listener(async_received_callback)

    await hass.async_add_executor_job(
        pywemo_registry.callbacks[device_wrapper.wemo.name], device_wrapper.wemo, "", ""
    )

    async with async_timeout.timeout(8):
        await got_callback.wait()
    assert device_wrapper.coordinator.last_update_success


async def test_subscription_update_action_exception(hass, pywemo_device, wemo_entity):
    """Device handles ActionException on get_state properly."""
    device_wrapper = wemo_device.async_get_device(hass, wemo_entity.device_id)
    device_wrapper.coordinator.last_update_success = True

    pywemo_device.subscription_update.return_value = False
    pywemo_device.get_state.reset_mock()
    pywemo_device.get_state.side_effect = ActionException
    await hass.async_add_executor_job(
        device_wrapper.subscription_callback, pywemo_device, "", ""
    )
    await hass.async_block_till_done()

    pywemo_device.get_state.assert_called_once_with(True)
    assert device_wrapper.coordinator.last_update_success is False
    assert isinstance(device_wrapper.coordinator.last_exception, UpdateFailed)


async def test_subscription_update_exception(hass, pywemo_device, wemo_entity):
    """Device handles Exception on get_state properly."""
    device_wrapper = wemo_device.async_get_device(hass, wemo_entity.device_id)
    device_wrapper.coordinator.last_update_success = True

    pywemo_device.subscription_update.return_value = False
    pywemo_device.get_state.reset_mock()
    pywemo_device.get_state.side_effect = Exception
    await hass.async_add_executor_job(
        device_wrapper.subscription_callback, pywemo_device, "", ""
    )
    await hass.async_block_till_done()

    pywemo_device.get_state.assert_called_once_with(True)
    assert device_wrapper.coordinator.last_update_success is False
    assert isinstance(device_wrapper.coordinator.last_exception, Exception)


async def test_async_update_data_subscribed(
    hass, pywemo_registry, pywemo_device, wemo_entity
):
    """No update happens when the device is subscribed."""
    device_wrapper = wemo_device.async_get_device(hass, wemo_entity.device_id)
    pywemo_registry.is_subscribed.return_value = True
    pywemo_device.get_state.reset_mock()
    await device_wrapper.async_update_data()
    pywemo_device.get_state.assert_not_called()
