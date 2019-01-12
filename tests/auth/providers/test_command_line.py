"""Tests for the command_line auth provider."""

from unittest.mock import Mock
import os
import uuid

import pytest

from homeassistant.auth import auth_store, models as auth_models, AuthManager
from homeassistant.auth.providers import command_line
from homeassistant.const import CONF_TYPE

from tests.common import mock_coro


@pytest.fixture
def store(hass):
    """Mock store."""
    return auth_store.AuthStore(hass)


@pytest.fixture
def provider(hass, store):
    """Mock provider."""
    return command_line.CommandLineAuthProvider(hass, store, {
        CONF_TYPE: "command_line",
        command_line.CONF_COMMAND: os.path.join(
            os.path.dirname(__file__), "test_command_line_cmd.sh"
        ),
        command_line.CONF_ARGS: [],
        command_line.CONF_META: False,
    })


@pytest.fixture
def manager(hass, store, provider):
    """Mock manager."""
    return AuthManager(hass, store, {
        (provider.type, provider.id): provider
    }, {})


async def test_create_new_credential(manager, provider):
    """Test that we create a new credential."""
    credentials = await provider.async_get_or_create_credentials({
        "username": "good-user",
        "password": "good-pass",
    })
    assert credentials.is_new is True

    user = await manager.async_get_or_create_user(credentials)
    assert user.is_active


async def test_match_existing_credentials(store, provider):
    """See if we match existing users."""
    existing = auth_models.Credentials(
        id=uuid.uuid4(),
        auth_provider_type="command_line",
        auth_provider_id=None,
        data={
            "username": "good-user"
        },
        is_new=False,
    )
    provider.async_credentials = Mock(return_value=mock_coro([existing]))
    credentials = await provider.async_get_or_create_credentials({
        "username": "good-user",
        "password": "irrelevant",
    })
    assert credentials is existing


async def test_invalid_username(provider):
    """Test we raise if incorrect user specified."""
    with pytest.raises(command_line.InvalidAuthError):
        await provider.async_validate_login("bad-user", "good-pass")


async def test_invalid_password(provider):
    """Test we raise if incorrect password specified."""
    with pytest.raises(command_line.InvalidAuthError):
        await provider.async_validate_login("good-user", "bad-pass")


async def test_good_auth(provider):
    """Test nothing is raised with good credentials."""
    await provider.async_validate_login("good-user", "good-pass")


async def test_good_auth_with_meta(manager, provider):
    """Test metadata is added upon successful authentication."""
    provider.config[command_line.CONF_ARGS] = ["--with-meta"]
    provider.config[command_line.CONF_META] = True

    await provider.async_validate_login("good-user", "good-pass")

    credentials = await provider.async_get_or_create_credentials({
        "username": "good-user",
        "password": "good-pass",
    })
    assert credentials.is_new is True

    user = await manager.async_get_or_create_user(credentials)
    assert user.name == "Bob"
    assert user.is_active


async def test_utf_8_username_password(provider):
    """Test that we create a new credential."""
    credentials = await provider.async_get_or_create_credentials({
        "username": "ßßß",
        "password": "äöü",
    })
    assert credentials.is_new is True
