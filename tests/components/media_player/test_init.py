"""Test the base functions of the media player."""
from http import HTTPStatus
from unittest.mock import patch

import pytest
import voluptuous as vol

from homeassistant.components.media_player import (
    ATTR_MEDIA_VOLUME_LEVEL,
    DOMAIN as MEDIA_PLAYER_DOMAIN,
    SERVICE_VOLUME_SET,
    SERVICE_VOLUME_UP,
    BrowseMedia,
    MediaClass,
    MediaPlayerEnqueue,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
)
from homeassistant.components.websocket_api.const import TYPE_RESULT
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component

from .common import MockMediaPlayer

from tests.test_util.aiohttp import AiohttpClientMocker
from tests.typing import ClientSessionGenerator, WebSocketGenerator


@pytest.fixture(autouse=True)
async def setup_homeassistant(hass: HomeAssistant):
    """Set up the homeassistant integration."""
    await async_setup_component(hass, "homeassistant", {})


async def test_get_image_http(
    hass: HomeAssistant, hass_client_no_auth: ClientSessionGenerator
) -> None:
    """Test get image via http command."""
    await async_setup_component(
        hass, "media_player", {"media_player": {"platform": "demo"}}
    )
    await hass.async_block_till_done()

    state = hass.states.get("media_player.bedroom")
    assert "entity_picture_local" not in state.attributes

    client = await hass_client_no_auth()

    with patch(
        "homeassistant.components.media_player.MediaPlayerEntity."
        "async_get_media_image",
        return_value=(b"image", "image/jpeg"),
    ):
        resp = await client.get(state.attributes["entity_picture"])
        content = await resp.read()

    assert content == b"image"


async def test_get_image_http_remote(
    hass: HomeAssistant, hass_client_no_auth: ClientSessionGenerator
) -> None:
    """Test get image url via http command."""
    with patch(
        "homeassistant.components.media_player.MediaPlayerEntity."
        "media_image_remotely_accessible",
        return_value=True,
    ):
        await async_setup_component(
            hass, "media_player", {"media_player": {"platform": "demo"}}
        )
        await hass.async_block_till_done()

        state = hass.states.get("media_player.bedroom")
        assert "entity_picture_local" in state.attributes

        client = await hass_client_no_auth()

        with patch(
            "homeassistant.components.media_player.MediaPlayerEntity."
            "async_get_media_image",
            return_value=(b"image", "image/jpeg"),
        ):
            resp = await client.get(state.attributes["entity_picture_local"])
            content = await resp.read()

        assert content == b"image"


async def test_get_image_http_log_credentials_redacted(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test credentials are redacted when logging url when fetching image."""
    url = "http://vi:pass@example.com/default.jpg"
    with patch(
        "homeassistant.components.demo.media_player.DemoYoutubePlayer.media_image_url",
        url,
    ):
        await async_setup_component(
            hass, "media_player", {"media_player": {"platform": "demo"}}
        )
        await hass.async_block_till_done()

        state = hass.states.get("media_player.bedroom")
        assert "entity_picture_local" not in state.attributes

        aioclient_mock.get(url, exc=TimeoutError())

        client = await hass_client_no_auth()

        resp = await client.get(state.attributes["entity_picture"])

    assert resp.status == HTTPStatus.INTERNAL_SERVER_ERROR
    assert f"Error retrieving proxied image from {url}" not in caplog.text
    assert (
        "Error retrieving proxied image from "
        f"{url.replace('pass', 'xxxxxxxx').replace('vi', 'xxxx')}"
    ) in caplog.text


async def test_get_async_get_browse_image(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Test get browse image."""
    await async_setup_component(
        hass, "media_player", {"media_player": {"platform": "demo"}}
    )
    await hass.async_block_till_done()

    entity_comp = hass.data.get("entity_components", {}).get("media_player")
    assert entity_comp

    player = entity_comp.get_entity("media_player.bedroom")
    assert player

    client = await hass_client_no_auth()

    with patch(
        "homeassistant.components.media_player.MediaPlayerEntity."
        "async_get_browse_image",
        return_value=(b"image", "image/jpeg"),
    ):
        url = player.get_browse_image_url("album", "abcd")
        resp = await client.get(url)
        content = await resp.read()

    assert content == b"image"


async def test_media_browse(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator
) -> None:
    """Test browsing media."""
    await async_setup_component(
        hass, "media_player", {"media_player": {"platform": "demo"}}
    )
    await hass.async_block_till_done()

    client = await hass_ws_client(hass)

    with patch(
        "homeassistant.components.media_player.MediaPlayerEntity.async_browse_media",
        return_value=BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id="mock-id",
            media_content_type="mock-type",
            title="Mock Title",
            can_play=False,
            can_expand=True,
        ),
    ) as mock_browse_media:
        await client.send_json(
            {
                "id": 5,
                "type": "media_player/browse_media",
                "entity_id": "media_player.browse",
                "media_content_type": "album",
                "media_content_id": "abcd",
            }
        )

        msg = await client.receive_json()

    assert msg["id"] == 5
    assert msg["type"] == TYPE_RESULT
    assert msg["success"]
    assert msg["result"] == {
        "title": "Mock Title",
        "media_class": "directory",
        "media_content_type": "mock-type",
        "media_content_id": "mock-id",
        "can_play": False,
        "can_expand": True,
        "children_media_class": None,
        "thumbnail": None,
        "not_shown": 0,
        "children": [],
    }
    assert mock_browse_media.mock_calls[0][1] == ("album", "abcd")

    with patch(
        "homeassistant.components.media_player.MediaPlayerEntity.async_browse_media",
        return_value={"bla": "yo"},
    ):
        await client.send_json(
            {
                "id": 6,
                "type": "media_player/browse_media",
                "entity_id": "media_player.browse",
            }
        )

        msg = await client.receive_json()

    assert msg["id"] == 6
    assert msg["type"] == TYPE_RESULT
    assert msg["success"]
    assert msg["result"] == {"bla": "yo"}


async def test_group_members_available_when_off(hass: HomeAssistant) -> None:
    """Test that group_members are still available when media_player is off."""
    await async_setup_component(
        hass, "media_player", {"media_player": {"platform": "demo"}}
    )
    await hass.async_block_till_done()

    await hass.services.async_call(
        "media_player",
        "turn_off",
        {ATTR_ENTITY_ID: "media_player.group"},
        blocking=True,
    )

    state = hass.states.get("media_player.group")
    assert state.state == STATE_OFF
    assert "group_members" in state.attributes


@pytest.mark.parametrize(
    ("input", "expected"),
    (
        (True, MediaPlayerEnqueue.ADD),
        (False, MediaPlayerEnqueue.PLAY),
        ("play", MediaPlayerEnqueue.PLAY),
        ("next", MediaPlayerEnqueue.NEXT),
        ("add", MediaPlayerEnqueue.ADD),
        ("replace", MediaPlayerEnqueue.REPLACE),
    ),
)
async def test_enqueue_rewrite(hass: HomeAssistant, input, expected) -> None:
    """Test that group_members are still available when media_player is off."""
    await async_setup_component(
        hass, "media_player", {"media_player": {"platform": "demo"}}
    )
    await hass.async_block_till_done()

    # Fake group support for DemoYoutubePlayer
    with patch(
        "homeassistant.components.demo.media_player.DemoYoutubePlayer.play_media",
    ) as mock_play_media:
        await hass.services.async_call(
            "media_player",
            "play_media",
            {
                "entity_id": "media_player.bedroom",
                "media_content_type": "music",
                "media_content_id": "1234",
                "enqueue": input,
            },
            blocking=True,
        )

    assert len(mock_play_media.mock_calls) == 1
    assert mock_play_media.mock_calls[0][2]["enqueue"] == expected


async def test_enqueue_alert_exclusive(hass: HomeAssistant) -> None:
    """Test that alert and enqueue cannot be used together."""
    await async_setup_component(
        hass, "media_player", {"media_player": {"platform": "demo"}}
    )
    await hass.async_block_till_done()

    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            "media_player",
            "play_media",
            {
                "entity_id": "media_player.bedroom",
                "media_content_type": "music",
                "media_content_id": "1234",
                "enqueue": "play",
                "announce": True,
            },
            blocking=True,
        )


async def test_get_async_get_browse_image_quoting(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Test get browse image using media_content_id with special characters.

    async_get_browse_image() should get called with the same string that is
    passed into get_browse_image_url().
    """
    await async_setup_component(
        hass, "media_player", {"media_player": {"platform": "demo"}}
    )
    await hass.async_block_till_done()

    entity_comp = hass.data.get("entity_components", {}).get("media_player")
    assert entity_comp

    player = entity_comp.get_entity("media_player.bedroom")
    assert player

    client = await hass_client_no_auth()

    with patch(
        "homeassistant.components.media_player.MediaPlayerEntity."
        "async_get_browse_image",
    ) as mock_browse_image:
        media_content_id = "a/b c/d+e%2Fg{}"
        url = player.get_browse_image_url("album", media_content_id)
        await client.get(url)
        mock_browse_image.assert_called_with("album", media_content_id, None)


def test_deprecated_supported_features_ints(caplog: pytest.LogCaptureFixture) -> None:
    """Test deprecated supported features ints."""

    class MockMediaPlayerEntity(MediaPlayerEntity):
        @property
        def supported_features(self) -> int:
            """Return supported features."""
            return 1

    entity = MockMediaPlayerEntity()
    assert entity.supported_features_compat is MediaPlayerEntityFeature(1)
    assert "MockMediaPlayerEntity" in caplog.text
    assert "is using deprecated supported features values" in caplog.text
    assert "Instead it should use" in caplog.text
    assert "MediaPlayerEntityFeature.PAUSE" in caplog.text
    caplog.clear()
    assert entity.supported_features_compat is MediaPlayerEntityFeature(1)
    assert "is using deprecated supported features values" not in caplog.text


async def test_volume_limit_set_volume(
    hass: HomeAssistant,
    setup: None,
    mock_media_player: MockMediaPlayer,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test volume limit."""
    entity_id = "media_player.test"
    mock_media_player._attr_supported_features = (
        MediaPlayerEntityFeature.VOLUME_SET | MediaPlayerEntityFeature.VOLUME_STEP
    )

    entry = entity_registry.async_get(entity_id)
    assert entry.options == {}

    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_VOLUME_SET,
        {ATTR_ENTITY_ID: entity_id, ATTR_MEDIA_VOLUME_LEVEL: 1.0},
        blocking=True,
    )
    mock_media_player.async_set_volume_level.assert_called_once_with(volume=1.0)
    mock_media_player.async_set_volume_level.reset_mock()

    # Set a volume limit
    entity_registry.async_update_entity_options(
        entity_id, MEDIA_PLAYER_DOMAIN, {"max_volume": 0.5}
    )
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_VOLUME_SET,
        {ATTR_ENTITY_ID: entity_id, ATTR_MEDIA_VOLUME_LEVEL: 1.0},
        blocking=True,
    )
    mock_media_player.async_set_volume_level.assert_called_once_with(volume=0.5)
    mock_media_player.async_set_volume_level.reset_mock()

    # Update the volume limit
    entity_registry.async_update_entity_options(
        entity_id, MEDIA_PLAYER_DOMAIN, {"max_volume": 0.8}
    )
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_VOLUME_SET,
        {ATTR_ENTITY_ID: entity_id, ATTR_MEDIA_VOLUME_LEVEL: 1.0},
        blocking=True,
    )
    mock_media_player.async_set_volume_level.assert_called_once_with(volume=0.8)


async def test_volume_limit_increase_volume(
    hass: HomeAssistant,
    setup: None,
    mock_media_player: MockMediaPlayer,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test volume limit."""
    entity_id = "media_player.test"
    mock_media_player._attr_supported_features = (
        MediaPlayerEntityFeature.VOLUME_SET | MediaPlayerEntityFeature.VOLUME_STEP
    )

    entry = entity_registry.async_get(entity_id)
    assert entry.options == {}

    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_VOLUME_UP,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    mock_media_player.async_volume_up.assert_called_once_with()
    mock_media_player.async_volume_up.reset_mock()

    mock_media_player._attr_volume_level = 1.0
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_VOLUME_UP,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    mock_media_player.async_volume_up.assert_called_once_with()
    mock_media_player.async_volume_up.reset_mock()

    # Set a volume limit
    mock_media_player._attr_volume_level = None
    entity_registry.async_update_entity_options(
        entity_id, MEDIA_PLAYER_DOMAIN, {"max_volume": 0.5}
    )
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_VOLUME_UP,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    mock_media_player.async_volume_up.assert_called_once_with()
    mock_media_player.async_volume_up.reset_mock()

    # 0.40 + 0.10 = 0.50 -> call not blocked
    mock_media_player._attr_volume_level = 0.40
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_VOLUME_UP,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    mock_media_player.async_volume_up.assert_called_once_with()
    mock_media_player.async_volume_up.reset_mock()

    # 0.41 + 0.10 > 0.50 -> call blocked
    mock_media_player._attr_volume_level = 0.41
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_VOLUME_UP,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    mock_media_player.async_volume_up.assert_not_called()
    mock_media_player.async_volume_up.reset_mock()

    # 0.41 + 0.05 < 0.50 -> call not blocked
    mock_media_player._attr_volume_step = 0.05
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_VOLUME_UP,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    mock_media_player.async_volume_up.assert_called_once_with()
    mock_media_player.async_volume_up.reset_mock()
