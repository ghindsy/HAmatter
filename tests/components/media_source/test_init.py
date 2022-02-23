"""Test Media Source initialization."""
from unittest.mock import Mock, patch

import pytest
import yarl

from homeassistant.components import media_source
from homeassistant.components.media_player import MEDIA_CLASS_DIRECTORY, BrowseError
from homeassistant.components.media_source import const
from homeassistant.setup import async_setup_component


async def test_is_media_source_id():
    """Test media source validation."""
    assert media_source.is_media_source_id(media_source.URI_SCHEME)
    assert media_source.is_media_source_id(f"{media_source.URI_SCHEME}domain")
    assert media_source.is_media_source_id(
        f"{media_source.URI_SCHEME}domain/identifier"
    )
    assert not media_source.is_media_source_id("test")


async def test_generate_media_source_id():
    """Test identifier generation."""
    tests = [
        (None, None),
        (None, ""),
        ("", ""),
        ("domain", None),
        ("domain", ""),
        ("domain", "identifier"),
    ]

    for domain, identifier in tests:
        assert media_source.is_media_source_id(
            media_source.generate_media_source_id(domain, identifier)
        )


async def test_async_browse_media(hass):
    """Test browse media."""
    assert await async_setup_component(hass, media_source.DOMAIN, {})
    await hass.async_block_till_done()

    # Test non-media ignored (/media has test.mp3 and not_media.txt)
    media = await media_source.async_browse_media(hass, "")
    assert isinstance(media, media_source.models.BrowseMediaSource)
    assert media.title == "media"
    assert len(media.children) == 2

    # Test content filter
    media = await media_source.async_browse_media(
        hass,
        "",
        content_filter=lambda item: item.media_content_type.startswith("video/"),
    )
    assert isinstance(media, media_source.models.BrowseMediaSource)
    assert media.title == "media"
    assert len(media.children) == 1, media.children
    media.children[0].title = "Epic Sax Guy 10 Hours"
    assert media.not_shown == 1

    # Test invalid media content
    with pytest.raises(BrowseError):
        await media_source.async_browse_media(hass, "invalid")

    # Test base URI returns all domains
    media = await media_source.async_browse_media(hass, const.URI_SCHEME)
    assert isinstance(media, media_source.models.BrowseMediaSource)
    assert len(media.children) == 1
    assert media.children[0].title == "Local Media"


async def test_async_resolve_media(hass):
    """Test browse media."""
    assert await async_setup_component(hass, media_source.DOMAIN, {})
    await hass.async_block_till_done()

    media = await media_source.async_resolve_media(
        hass,
        media_source.generate_media_source_id(media_source.DOMAIN, "local/test.mp3"),
    )
    assert isinstance(media, media_source.models.PlayMedia)
    assert media.url == "/media/local/test.mp3"
    assert media.mime_type == "audio/mpeg"


async def test_async_unresolve_media(hass):
    """Test browse media."""
    assert await async_setup_component(hass, media_source.DOMAIN, {})
    await hass.async_block_till_done()

    # Test no media content
    with pytest.raises(media_source.Unresolvable):
        await media_source.async_resolve_media(hass, "")

    # Test invalid media content
    with pytest.raises(media_source.Unresolvable):
        await media_source.async_resolve_media(hass, "invalid")


async def test_websocket_browse_media(hass, hass_ws_client):
    """Test browse media websocket."""
    assert await async_setup_component(hass, media_source.DOMAIN, {})
    await hass.async_block_till_done()

    client = await hass_ws_client(hass)

    media = media_source.models.BrowseMediaSource(
        domain=media_source.DOMAIN,
        identifier="/media",
        title="Local Media",
        media_class=MEDIA_CLASS_DIRECTORY,
        media_content_type="listing",
        can_play=False,
        can_expand=True,
    )

    with patch(
        "homeassistant.components.media_source.async_browse_media",
        return_value=media,
    ):
        await client.send_json(
            {
                "id": 1,
                "type": "media_source/browse_media",
            }
        )

        msg = await client.receive_json()

    assert msg["success"]
    assert msg["id"] == 1
    assert media.as_dict() == msg["result"]

    with patch(
        "homeassistant.components.media_source.async_browse_media",
        side_effect=BrowseError("test"),
    ):
        await client.send_json(
            {
                "id": 2,
                "type": "media_source/browse_media",
                "media_content_id": "invalid",
            }
        )

        msg = await client.receive_json()

    assert not msg["success"]
    assert msg["error"]["code"] == "browse_media_failed"
    assert msg["error"]["message"] == "test"


@pytest.mark.parametrize("filename", ["test.mp3", "Epic Sax Guy 10 Hours.mp4"])
async def test_websocket_resolve_media(hass, hass_ws_client, filename):
    """Test browse media websocket."""
    assert await async_setup_component(hass, media_source.DOMAIN, {})
    await hass.async_block_till_done()

    client = await hass_ws_client(hass)

    media = media_source.models.PlayMedia(
        f"/media/local/{filename}",
        "audio/mpeg",
    )

    with patch(
        "homeassistant.components.media_source.async_resolve_media",
        return_value=media,
    ):
        await client.send_json(
            {
                "id": 1,
                "type": "media_source/resolve_media",
                "media_content_id": f"{const.URI_SCHEME}{media_source.DOMAIN}/local/{filename}",
            }
        )

        msg = await client.receive_json()

    assert msg["success"]
    assert msg["id"] == 1
    assert msg["result"]["mime_type"] == media.mime_type

    # Validate url is signed.
    parsed = yarl.URL(msg["result"]["url"])
    assert parsed.path == getattr(media, "url")
    assert "authSig" in parsed.query

    with patch(
        "homeassistant.components.media_source.async_resolve_media",
        side_effect=media_source.Unresolvable("test"),
    ):
        await client.send_json(
            {
                "id": 2,
                "type": "media_source/resolve_media",
                "media_content_id": "invalid",
            }
        )

        msg = await client.receive_json()

    assert not msg["success"]
    assert msg["error"]["code"] == "resolve_media_failed"
    assert msg["error"]["message"] == "test"


async def test_browse_resolve_without_setup():
    """Test browse and resolve work without being setup."""
    with pytest.raises(BrowseError):
        await media_source.async_browse_media(Mock(data={}), None)

    with pytest.raises(media_source.Unresolvable):
        await media_source.async_resolve_media(Mock(data={}), None)
