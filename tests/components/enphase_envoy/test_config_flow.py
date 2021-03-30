"""Test the Enphase Envoy config flow."""
from unittest.mock import MagicMock, patch

import httpx

from homeassistant import config_entries, setup
from homeassistant.components.enphase_envoy.const import DOMAIN
from homeassistant.core import HomeAssistant


async def test_form(hass: HomeAssistant) -> None:
    """Test we get the form."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["errors"] == {}

    with patch(
        "homeassistant.components.enphase_envoy.config_flow.EnvoyReader.getData",
        return_value=True,
    ), patch(
        "homeassistant.components.enphase_envoy.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "1.1.1.1",
                "username": "test-username",
                "password": "test-password",
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == "create_entry"
    assert result2["title"] == "Envoy"
    assert result2["data"] == {
        "host": "1.1.1.1",
        "name": "Envoy",
        "username": "test-username",
        "password": "test-password",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_auth(hass: HomeAssistant) -> None:
    """Test we handle invalid auth."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.enphase_envoy.config_flow.EnvoyReader.getData",
        side_effect=httpx.HTTPStatusError(
            "any", request=MagicMock(), response=MagicMock()
        ),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "1.1.1.1",
                "username": "test-username",
                "password": "test-password",
            },
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_form_cannot_connect(hass: HomeAssistant) -> None:
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.enphase_envoy.config_flow.EnvoyReader.getData",
        side_effect=httpx.HTTPError("any", request=MagicMock()),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "1.1.1.1",
                "username": "test-username",
                "password": "test-password",
            },
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_import(hass: HomeAssistant) -> None:
    """Test we can import from yaml."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    with patch(
        "homeassistant.components.enphase_envoy.config_flow.EnvoyReader.getData",
        return_value=True,
    ), patch(
        "homeassistant.components.enphase_envoy.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "import"},
            data={
                "ip_address": "1.1.1.1",
                "name": "Pool Envoy",
                "username": "test-username",
                "password": "test-password",
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == "create_entry"
    assert result2["title"] == "Pool Envoy"
    assert result2["data"] == {
        "host": "1.1.1.1",
        "name": "Pool Envoy",
        "username": "test-username",
        "password": "test-password",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_zeroconf(hass: HomeAssistant) -> None:
    """Test we can setup from zeroconf."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "zeroconf"},
        data={
            "properties": {"serialnum": "1234"},
            "host": "1.1.1.1",
        },
    )
    await hass.async_block_till_done()

    assert result["type"] == "form"
    assert result["step_id"] == "user"

    with patch(
        "homeassistant.components.enphase_envoy.config_flow.EnvoyReader.getData",
        return_value=True,
    ), patch(
        "homeassistant.components.enphase_envoy.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "1.1.1.1",
                "username": "test-username",
                "password": "test-password",
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == "create_entry"
    assert result2["title"] == "Envoy 1234"
    assert result2["data"] == {
        "host": "1.1.1.1",
        "name": "Envoy 1234",
        "username": "test-username",
        "password": "test-password",
    }
    assert len(mock_setup_entry.mock_calls) == 1
