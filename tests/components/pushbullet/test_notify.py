"""The tests for the pushbullet notification platform."""
import json

from pushbullet import PushBullet

import homeassistant.components.notify as notify
from homeassistant.setup import async_setup_component

from tests.async_mock import patch
from tests.common import assert_setup_component, load_fixture


@patch.object(
    PushBullet,
    "_get_data",
    return_value=json.loads(load_fixture("pushbullet_devices.json")),
)
async def test_pushbullet_config(mock__get_data, hass):
    """Test setup."""
    config = {
        notify.DOMAIN: {
            "name": "test",
            "platform": "pushbullet",
            "api_key": "MYFAKEKEY",
        }
    }
    with assert_setup_component(1) as handle_config:
        assert await async_setup_component(hass, notify.DOMAIN, config)
        await hass.async_block_till_done()
    assert handle_config[notify.DOMAIN]


async def test_pushbullet_config_bad(hass):
    """Test set up the platform with bad/missing configuration."""
    config = {notify.DOMAIN: {"platform": "pushbullet"}}
    with assert_setup_component(0) as handle_config:
        assert await async_setup_component(hass, notify.DOMAIN, config)
        await hass.async_block_till_done()
    assert not handle_config[notify.DOMAIN]


@patch.object(
    PushBullet,
    "_get_data",
    return_value=json.loads(load_fixture("pushbullet_devices.json")),
)
async def test_pushbullet_push_default(mock__get_data, hass, requests_mock):
    """Test pushbullet push to default target."""
    config = {
        notify.DOMAIN: {
            "name": "test",
            "platform": "pushbullet",
            "api_key": "MYFAKEKEY",
        }
    }
    with assert_setup_component(1) as handle_config:
        assert await async_setup_component(hass, notify.DOMAIN, config)
        await hass.async_block_till_done()
    assert handle_config[notify.DOMAIN]
    requests_mock.register_uri(
        "POST",
        "https://api.pushbullet.com/v2/pushes",
        status_code=200,
        json={"mock_response": "Ok"},
    )
    data = {"title": "Test Title", "message": "Test Message"}
    await hass.services.async_call(notify.DOMAIN, "test", data)
    await hass.async_block_till_done()
    assert requests_mock.called
    assert requests_mock.call_count == 1

    expected_body = {"body": "Test Message", "title": "Test Title", "type": "note"}
    assert requests_mock.last_request.json() == expected_body


@patch.object(
    PushBullet,
    "_get_data",
    return_value=json.loads(load_fixture("pushbullet_devices.json")),
)
async def test_pushbullet_push_device(mock__get_data, hass, requests_mock):
    """Test pushbullet push to default target."""
    config = {
        notify.DOMAIN: {
            "name": "test",
            "platform": "pushbullet",
            "api_key": "MYFAKEKEY",
        }
    }
    with assert_setup_component(1) as handle_config:
        assert await async_setup_component(hass, notify.DOMAIN, config)
        await hass.async_block_till_done()
    assert handle_config[notify.DOMAIN]
    requests_mock.register_uri(
        "POST",
        "https://api.pushbullet.com/v2/pushes",
        status_code=200,
        json={"mock_response": "Ok"},
    )
    data = {
        "title": "Test Title",
        "message": "Test Message",
        "target": ["device/DESKTOP"],
    }
    await hass.services.async_call(notify.DOMAIN, "test", data)
    await hass.async_block_till_done()
    assert requests_mock.called
    assert requests_mock.call_count == 1

    expected_body = {
        "body": "Test Message",
        "device_iden": "identity1",
        "title": "Test Title",
        "type": "note",
    }
    assert requests_mock.last_request.json() == expected_body


@patch.object(
    PushBullet,
    "_get_data",
    return_value=json.loads(load_fixture("pushbullet_devices.json")),
)
async def test_pushbullet_push_devices(mock__get_data, hass, requests_mock):
    """Test pushbullet push to default target."""
    config = {
        notify.DOMAIN: {
            "name": "test",
            "platform": "pushbullet",
            "api_key": "MYFAKEKEY",
        }
    }
    with assert_setup_component(1) as handle_config:
        assert await async_setup_component(hass, notify.DOMAIN, config)
        await hass.async_block_till_done()
    assert handle_config[notify.DOMAIN]
    requests_mock.register_uri(
        "POST",
        "https://api.pushbullet.com/v2/pushes",
        status_code=200,
        json={"mock_response": "Ok"},
    )
    data = {
        "title": "Test Title",
        "message": "Test Message",
        "target": ["device/DESKTOP", "device/My iPhone"],
    }
    await hass.services.async_call(notify.DOMAIN, "test", data)
    await hass.async_block_till_done()
    assert requests_mock.called
    assert requests_mock.call_count == 2
    assert len(requests_mock.request_history) == 2

    expected_body = {
        "body": "Test Message",
        "device_iden": "identity1",
        "title": "Test Title",
        "type": "note",
    }
    assert requests_mock.request_history[0].json() == expected_body
    expected_body = {
        "body": "Test Message",
        "device_iden": "identity2",
        "title": "Test Title",
        "type": "note",
    }
    assert requests_mock.request_history[1].json() == expected_body


@patch.object(
    PushBullet,
    "_get_data",
    return_value=json.loads(load_fixture("pushbullet_devices.json")),
)
async def test_pushbullet_push_email(mock__get_data, hass, requests_mock):
    """Test pushbullet push to default target."""
    config = {
        notify.DOMAIN: {
            "name": "test",
            "platform": "pushbullet",
            "api_key": "MYFAKEKEY",
        }
    }
    with assert_setup_component(1) as handle_config:
        assert await async_setup_component(hass, notify.DOMAIN, config)
        await hass.async_block_till_done()
    assert handle_config[notify.DOMAIN]
    requests_mock.register_uri(
        "POST",
        "https://api.pushbullet.com/v2/pushes",
        status_code=200,
        json={"mock_response": "Ok"},
    )
    data = {
        "title": "Test Title",
        "message": "Test Message",
        "target": ["email/user@host.net"],
    }
    await hass.services.async_call(notify.DOMAIN, "test", data)
    await hass.async_block_till_done()
    assert requests_mock.called
    assert requests_mock.call_count == 1
    assert len(requests_mock.request_history) == 1

    expected_body = {
        "body": "Test Message",
        "email": "user@host.net",
        "title": "Test Title",
        "type": "note",
    }
    assert requests_mock.request_history[0].json() == expected_body


@patch.object(
    PushBullet,
    "_get_data",
    return_value=json.loads(load_fixture("pushbullet_devices.json")),
)
async def test_pushbullet_push_mixed(mock__get_data, hass, requests_mock):
    """Test pushbullet push to default target."""
    config = {
        notify.DOMAIN: {
            "name": "test",
            "platform": "pushbullet",
            "api_key": "MYFAKEKEY",
        }
    }
    with assert_setup_component(1) as handle_config:
        assert await async_setup_component(hass, notify.DOMAIN, config)
        await hass.async_block_till_done()
    assert handle_config[notify.DOMAIN]
    requests_mock.register_uri(
        "POST",
        "https://api.pushbullet.com/v2/pushes",
        status_code=200,
        json={"mock_response": "Ok"},
    )
    data = {
        "title": "Test Title",
        "message": "Test Message",
        "target": ["device/DESKTOP", "email/user@host.net"],
    }
    await hass.services.async_call(notify.DOMAIN, "test", data)
    await hass.async_block_till_done()
    assert requests_mock.called
    assert requests_mock.call_count == 2
    assert len(requests_mock.request_history) == 2

    expected_body = {
        "body": "Test Message",
        "device_iden": "identity1",
        "title": "Test Title",
        "type": "note",
    }
    assert requests_mock.request_history[0].json() == expected_body
    expected_body = {
        "body": "Test Message",
        "email": "user@host.net",
        "title": "Test Title",
        "type": "note",
    }
    assert requests_mock.request_history[1].json() == expected_body


@patch.object(
    PushBullet,
    "_get_data",
    return_value=json.loads(load_fixture("pushbullet_devices.json")),
)
async def test_pushbullet_push_no_file(mock__get_data, hass, requests_mock):
    """Test pushbullet push to default target."""
    config = {
        notify.DOMAIN: {
            "name": "test",
            "platform": "pushbullet",
            "api_key": "MYFAKEKEY",
        }
    }
    with assert_setup_component(1) as handle_config:
        assert await async_setup_component(hass, notify.DOMAIN, config)
        await hass.async_block_till_done()
    assert handle_config[notify.DOMAIN]
    requests_mock.register_uri(
        "POST",
        "https://api.pushbullet.com/v2/pushes",
        status_code=200,
        json={"mock_response": "Ok"},
    )
    data = {
        "title": "Test Title",
        "message": "Test Message",
        "target": ["device/DESKTOP", "device/My iPhone"],
        "data": {"file": "not_a_file"},
    }
    assert not await hass.services.async_call(notify.DOMAIN, "test", data)
    await hass.async_block_till_done()
