"""Tests for the mobile_app HTTP API."""
import json
from unittest.mock import patch

import pytest

from homeassistant.components.mobile_app.const import CONF_SECRET, DOMAIN
from homeassistant.const import CONF_WEBHOOK_ID
from homeassistant.setup import async_setup_component

from .const import (
    REGISTER,
    REGISTER_CLEARTEXT,
    REGISTER_CLEARTEXT_DUPLICATE_NAME,
    RENDER_TEMPLATE,
)

from tests.common import mock_coro


async def test_registration(hass, hass_client, hass_admin_user):
    """Test that registrations happen."""
    await async_setup_component(hass, DOMAIN, {DOMAIN: {}})

    api_client = await hass_client()

    with patch(
        "homeassistant.components.person.async_add_user_device_tracker",
        spec=True,
        return_value=mock_coro(),
    ) as add_user_dev_track:
        resp = await api_client.post(
            "/api/mobile_app/registrations", json=REGISTER_CLEARTEXT
        )

    assert len(add_user_dev_track.mock_calls) == 1
    assert add_user_dev_track.mock_calls[0][1][1] == hass_admin_user.id
    assert add_user_dev_track.mock_calls[0][1][2] == "device_tracker.test_clear"

    assert resp.status == 201
    register_json = await resp.json()
    assert CONF_WEBHOOK_ID in register_json
    assert CONF_SECRET in register_json

    entries = hass.config_entries.async_entries(DOMAIN)

    assert entries[0].unique_id == "io.homeassistant.mobile_app_test-mock-device-id"
    assert entries[0].data["device_id"] == REGISTER_CLEARTEXT["device_id"]
    assert entries[0].data["app_data"] == REGISTER_CLEARTEXT["app_data"]
    assert entries[0].data["app_id"] == REGISTER_CLEARTEXT["app_id"]
    assert entries[0].data["app_name"] == REGISTER_CLEARTEXT["app_name"]
    assert entries[0].data["app_version"] == REGISTER_CLEARTEXT["app_version"]
    assert entries[0].data["device_name"] == REGISTER_CLEARTEXT["device_name"]
    assert entries[0].data["manufacturer"] == REGISTER_CLEARTEXT["manufacturer"]
    assert entries[0].data["model"] == REGISTER_CLEARTEXT["model"]
    assert entries[0].data["os_name"] == REGISTER_CLEARTEXT["os_name"]
    assert entries[0].data["os_version"] == REGISTER_CLEARTEXT["os_version"]
    assert (
        entries[0].data["supports_encryption"]
        == REGISTER_CLEARTEXT["supports_encryption"]
    )


async def test_registration_encryption(hass, hass_client):
    """Test that registrations happen."""
    try:
        from nacl.secret import SecretBox
        from nacl.encoding import Base64Encoder
    except (ImportError, OSError):
        pytest.skip("libnacl/libsodium is not installed")
        return

    await async_setup_component(hass, DOMAIN, {DOMAIN: {}})

    api_client = await hass_client()

    resp = await api_client.post("/api/mobile_app/registrations", json=REGISTER)

    assert resp.status == 201
    register_json = await resp.json()

    keylen = SecretBox.KEY_SIZE
    key = register_json[CONF_SECRET].encode("utf-8")
    key = key[:keylen]
    key = key.ljust(keylen, b"\0")

    payload = json.dumps(RENDER_TEMPLATE["data"]).encode("utf-8")

    data = SecretBox(key).encrypt(payload, encoder=Base64Encoder).decode("utf-8")

    container = {"type": "render_template", "encrypted": True, "encrypted_data": data}

    resp = await api_client.post(
        "/api/webhook/{}".format(register_json[CONF_WEBHOOK_ID]), json=container
    )

    assert resp.status == 200

    webhook_json = await resp.json()
    assert "encrypted_data" in webhook_json

    decrypted_data = SecretBox(key).decrypt(
        webhook_json["encrypted_data"], encoder=Base64Encoder
    )
    decrypted_data = decrypted_data.decode("utf-8")

    assert json.loads(decrypted_data) == {"one": "Hello world"}


async def test_duplicate_device_name(hass, hass_client, hass_admin_user):
    """Test that registering duplicate device name adds suffix."""
    await async_setup_component(hass, DOMAIN, {DOMAIN: {}})

    api_client = await hass_client()

    # Register first device
    with patch(
        "homeassistant.components.person.async_add_user_device_tracker",
        spec=True,
        return_value=mock_coro(),
    ) as add_user_dev_track:
        resp = await api_client.post(
            "/api/mobile_app/registrations", json=REGISTER_CLEARTEXT
        )

    assert resp.status == 201

    assert len(add_user_dev_track.mock_calls) == 1
    assert add_user_dev_track.mock_calls[0][1][2] == "device_tracker.test_clear"

    # Register second device with same name
    with patch(
        "homeassistant.components.person.async_add_user_device_tracker",
        spec=True,
        return_value=mock_coro(),
    ) as add_user_dev_track:
        resp = await api_client.post(
            "/api/mobile_app/registrations", json=REGISTER_CLEARTEXT_DUPLICATE_NAME
        )

    assert resp.status == 201

    assert len(add_user_dev_track.mock_calls) == 1
    assert add_user_dev_track.mock_calls[0][1][2] == "device_tracker.test_clear_2"

    entries = hass.config_entries.async_entries(DOMAIN)

    assert entries[0].data["device_name"] == REGISTER_CLEARTEXT["device_name"]
    assert (
        entries[1].data["device_name"]
        == REGISTER_CLEARTEXT_DUPLICATE_NAME["device_name"] + "_2"
    )
