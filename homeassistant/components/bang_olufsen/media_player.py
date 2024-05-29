"""Media player entity for the Bang & Olufsen integration."""

from __future__ import annotations

import contextlib
import json
import logging
from typing import Any, cast

from mozart_api import __version__ as MOZART_API_VERSION
from mozart_api.exceptions import ApiException, NotFoundException
from mozart_api.models import (
    Action,
    Art,
    BeolinkLeader,
    OverlayPlayRequest,
    PlaybackContentMetadata,
    PlaybackError,
    PlaybackProgress,
    PlayQueueItem,
    PlayQueueItemType,
    RenderingState,
    SceneProperties,
    SoftwareUpdateState,
    SoftwareUpdateStatus,
    Source,
    Uri,
    UserFlow,
    VolumeLevel,
    VolumeMute,
    VolumeState,
)
from mozart_api.mozart_client import MozartClient, get_highest_resolution_artwork
import voluptuous as vol

from homeassistant.components import media_source
from homeassistant.components.media_player import (
    ATTR_MEDIA_EXTRA,
    BrowseMedia,
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
    async_process_play_media_url,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MODEL, Platform
from homeassistant.core import (
    HomeAssistant,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
)
from homeassistant.helpers.device_registry import DeviceEntry, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback,
    async_get_current_platform,
)
from homeassistant.util.dt import utcnow

from . import BangOlufsenData
from .const import (
    BANG_OLUFSEN_STATES,
    CONF_BEOLINK_JID,
    CONNECTION_STATUS,
    DOMAIN,
    FALLBACK_SOURCES,
    HIDDEN_SOURCE_IDS,
    VALID_MEDIA_TYPES,
    BangOlufsenMediaType,
    BangOlufsenSource,
    WebsocketNotification,
)
from .entity import BangOlufsenEntity

_LOGGER = logging.getLogger(__name__)

BANG_OLUFSEN_FEATURES = (
    MediaPlayerEntityFeature.BROWSE_MEDIA
    | MediaPlayerEntityFeature.CLEAR_PLAYLIST
    | MediaPlayerEntityFeature.GROUPING
    | MediaPlayerEntityFeature.NEXT_TRACK
    | MediaPlayerEntityFeature.PAUSE
    | MediaPlayerEntityFeature.PLAY
    | MediaPlayerEntityFeature.PLAY_MEDIA
    | MediaPlayerEntityFeature.PREVIOUS_TRACK
    | MediaPlayerEntityFeature.SEEK
    | MediaPlayerEntityFeature.SELECT_SOURCE
    | MediaPlayerEntityFeature.STOP
    | MediaPlayerEntityFeature.TURN_OFF
    | MediaPlayerEntityFeature.VOLUME_MUTE
    | MediaPlayerEntityFeature.VOLUME_SET
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a Media Player entity from config entry."""
    data: BangOlufsenData = hass.data[DOMAIN][config_entry.entry_id]

    # Add MediaPlayer entity
    async_add_entities(new_entities=[BangOlufsenMediaPlayer(config_entry, data.client)])

    # Register services.
    platform = async_get_current_platform()

    platform.async_register_entity_service(
        name="beolink_join",
        schema={
            vol.Optional("beolink_jid"): vol.Match(
                r"(^\d{4})[.](\d{7})[.](\d{8})(@products\.bang-olufsen\.com)$"
            )
        },
        func="async_beolink_join",
        supports_response=SupportsResponse.OPTIONAL,
    )

    platform.async_register_entity_service(
        name="beolink_expand",
        schema={
            vol.Exclusive("all_discovered", "devices", ""): cv.boolean,
            vol.Exclusive(
                "beolink_jids",
                "devices",
                "Define either specific Beolink JIDs or all discovered",
            ): vol.All(
                cv.ensure_list,
                [
                    vol.Match(
                        r"(^\d{4})[.](\d{7})[.](\d{8})(@products\.bang-olufsen\.com)$"
                    )
                ],
            ),
        },
        func="async_beolink_expand",
        supports_response=SupportsResponse.OPTIONAL,
    )

    platform.async_register_entity_service(
        name="beolink_unexpand",
        schema={
            vol.Required("beolink_jids"): vol.All(
                cv.ensure_list,
                [
                    vol.Match(
                        r"(^\d{4})[.](\d{7})[.](\d{8})(@products\.bang-olufsen\.com)$"
                    )
                ],
            ),
        },
        func="async_beolink_unexpand",
    )

    platform.async_register_entity_service(
        name="beolink_leave",
        schema=None,
        func="async_beolink_leave",
    )

    platform.async_register_entity_service(
        name="beolink_allstandby",
        schema=None,
        func="async_beolink_allstandby",
    )


class BangOlufsenMediaPlayer(BangOlufsenEntity, MediaPlayerEntity):
    """Representation of a media player."""

    _attr_icon = "mdi:speaker-wireless"
    _attr_name = None
    _attr_device_class = MediaPlayerDeviceClass.SPEAKER
    _attr_supported_features = BANG_OLUFSEN_FEATURES

    def __init__(self, entry: ConfigEntry, client: MozartClient) -> None:
        """Initialize the media player."""
        super().__init__(entry, client)

        self._beolink_jid: str = self.entry.data[CONF_BEOLINK_JID]
        self._model: str = self.entry.data[CONF_MODEL]

        self._attr_device_info = DeviceInfo(
            configuration_url=f"http://{self._host}/#/",
            identifiers={(DOMAIN, self._unique_id)},
            manufacturer="Bang & Olufsen",
            model=self._model,
            serial_number=self._unique_id,
        )
        self._attr_unique_id = self._unique_id

        # Misc. variables.
        self._audio_sources: dict[str, str] = {}
        self._media_image: Art = Art()
        self._software_status: SoftwareUpdateStatus = SoftwareUpdateStatus(
            software_version="",
            state=SoftwareUpdateState(seconds_remaining=0, value="idle"),
        )
        self._sources: dict[str, str] = {}
        self._state: str = MediaPlayerState.IDLE
        self._video_sources: dict[str, str] = {}

        # Beolink
        self._beolink_sources: dict[str, bool] = {}
        self._remote_leader: BeolinkLeader | None = None
        self._beolink_attribute: dict[str, dict] = {}

    async def async_added_to_hass(self) -> None:
        """Turn on the dispatchers."""
        await self._initialize()

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{self._unique_id}_{CONNECTION_STATUS}",
                self._async_update_connection_state,
            )
        )

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{self._unique_id}_{WebsocketNotification.PLAYBACK_ERROR}",
                self._async_update_playback_error,
            )
        )

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{self._unique_id}_{WebsocketNotification.PLAYBACK_METADATA}",
                self._async_update_playback_metadata,
            )
        )

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{self._unique_id}_{WebsocketNotification.PLAYBACK_PROGRESS}",
                self._async_update_playback_progress,
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{self._unique_id}_{WebsocketNotification.PLAYBACK_STATE}",
                self._async_update_playback_state,
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{self._unique_id}_{WebsocketNotification.REMOTE_MENU_CHANGED}",
                self._update_sources,
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{self._unique_id}_{WebsocketNotification.SOURCE_CHANGE}",
                self._async_update_source_change,
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{self._unique_id}_{WebsocketNotification.VOLUME}",
                self._async_update_volume,
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{self._unique_id}_{WebsocketNotification.BEOLINK}",
                self._update_beolink,
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{self._unique_id}_{WebsocketNotification.CONFIGURATION}",
                self._update_name_and_beolink,
            )
        )

    async def _initialize(self) -> None:
        """Initialize connection dependent variables."""

        # Get software version.
        self._software_status = await self._client.get_softwareupdate_status()

        _LOGGER.debug(
            "Connected to: %s %s running SW %s",
            self._model,
            self._unique_id,
            self._software_status.software_version,
        )

        # Get overall device state once. This is handled by WebSocket events the rest of the time.
        product_state = await self._client.get_product_state()

        # Get volume information.
        if product_state.volume:
            self._volume = product_state.volume

        # Get all playback information.
        # Ensure that the metadata is not None upon startup
        if product_state.playback:
            if product_state.playback.metadata:
                self._playback_metadata = product_state.playback.metadata
                self._remote_leader = product_state.playback.metadata.remote_leader
            if product_state.playback.progress:
                self._playback_progress = product_state.playback.progress
            if product_state.playback.source:
                self._source_change = product_state.playback.source
            if product_state.playback.state:
                self._playback_state = product_state.playback.state
                # Set initial state
                if self._playback_state.value:
                    self._state = self._playback_state.value

        self._attr_media_position_updated_at = utcnow()

        # Get the highest resolution available of the given images.
        self._media_image = get_highest_resolution_artwork(self._playback_metadata)

        # If the device has been updated with new sources, then the API will fail here.
        await self._update_sources()

        # Update beolink attributes and device name.
        await self._update_name_and_beolink()

    async def _update_sources(self, update_ha_state: bool = False) -> None:
        """Get sources for the specific product."""

        # Audio sources
        try:
            # Get all available sources.
            sources = await self._client.get_available_sources(target_remote=False)

        # Use a fallback list of sources
        except ValueError:
            # Try to get software version from device
            if self.device_info:
                sw_version = self.device_info.get("sw_version")
            if not sw_version:
                sw_version = self._software_status.software_version

            _LOGGER.warning(
                "The API is outdated compared to the device software version %s and %s. Using fallback sources",
                MOZART_API_VERSION,
                sw_version,
            )
            sources = FALLBACK_SOURCES

        # Save all of the relevant enabled sources, both the ID and the friendly name for displaying in a dict.
        self._audio_sources = {
            source.id: source.name
            for source in cast(list[Source], sources.items)
            if source.is_enabled
            and source.id
            and source.name
            and source.id not in HIDDEN_SOURCE_IDS
        }

        # Some sources are not Beolink expandable. _source_change, which is used throughout the entity does not have this information.
        # Save expandable sources for Beolink services
        self._beolink_sources = {
            source.id: (
                source.is_multiroom_available
                if source.is_multiroom_available is not None
                else False
            )
            for source in cast(list[Source], sources.items)
            if source.id
        }

        # Video sources from remote menu
        menu_items = await self._client.get_remote_menu()

        for key in menu_items:
            menu_item = menu_items[key]

            if not menu_item.available:
                continue

            # TV SOURCES
            if (
                menu_item.content is not None
                and menu_item.content.categories
                and len(menu_item.content.categories) > 0
                and "music" not in menu_item.content.categories
                and menu_item.label
                and menu_item.label != "TV"
            ):
                self._video_sources[key] = menu_item.label

        # Combine the source dicts
        self._sources = self._audio_sources | self._video_sources

        self._attr_source_list = list(self._sources.values())

        if update_ha_state:
            self.async_write_ha_state()

    @callback
    async def _async_update_playback_metadata(
        self, data: PlaybackContentMetadata
    ) -> None:
        """Update _playback_metadata and related."""
        self._playback_metadata = data

        # Update current artwork and remote_leader.
        self._media_image = get_highest_resolution_artwork(self._playback_metadata)
        await self._update_beolink(should_update=False)

        self.async_write_ha_state()

    @callback
    def _async_update_playback_error(self, data: PlaybackError) -> None:
        """Show playback error."""
        _LOGGER.error(data.error)

    @callback
    def _async_update_playback_progress(self, data: PlaybackProgress) -> None:
        """Update _playback_progress and last update."""
        self._playback_progress = data
        self._attr_media_position_updated_at = utcnow()

        self.async_write_ha_state()

    @callback
    def _async_update_playback_state(self, data: RenderingState) -> None:
        """Update _playback_state and related."""
        self._playback_state = data

        # Update entity state based on the playback state.
        if self._playback_state.value:
            self._state = self._playback_state.value

            self.async_write_ha_state()

    @callback
    def _async_update_source_change(self, data: Source) -> None:
        """Update _source_change and related."""
        self._source_change = data

        # Check if source is line-in or optical and progress should be updated
        if self._source_change.id in (
            BangOlufsenSource.LINE_IN,
            BangOlufsenSource.SPDIF,
        ):
            self._playback_progress = PlaybackProgress(progress=0)

        self.async_write_ha_state()

    @callback
    def _async_update_volume(self, data: VolumeState) -> None:
        """Update _volume."""
        self._volume = data

        self.async_write_ha_state()

    async def _update_name_and_beolink(self) -> None:
        """Update the device friendly name."""
        beolink_self = await self._client.get_beolink_self()

        # Update device name
        device_registry = dr.async_get(self.hass)
        device_registry.async_update_device(
            device_id=cast(DeviceEntry, self.device_entry).id,
            name=beolink_self.friendly_name,
        )

        await self._update_beolink(should_update=False)

        self.async_write_ha_state()

    async def _update_beolink(self, should_update: bool = True) -> None:
        """Update the current Beolink leader, listeners, peers and self."""

        self._beolink_attribute = {}

        # Add Beolink self
        assert self.device_entry

        self._beolink_attribute = {
            "beolink": {"self": {self.device_entry.name: self._beolink_jid}}
        }

        # Add Beolink peers
        peers = await self._client.get_beolink_peers()

        if len(peers) > 0:
            self._beolink_attribute["beolink"]["peers"] = {}
            for peer in peers:
                self._beolink_attribute["beolink"]["peers"][peer.friendly_name] = (
                    peer.jid
                )

        self._remote_leader = self._playback_metadata.remote_leader

        # Temp fix for mismatch in WebSocket metadata and "real" REST endpoint where the remote leader is not deleted.
        if self.source in (
            BangOlufsenSource.LINE_IN,
            BangOlufsenSource.URI_STREAMER,
        ):
            self._remote_leader = None

        # Add Beolink listeners / leader

        # Create group members list
        group_members = []

        # If the device is a listener.
        if self._remote_leader is not None:
            # Add leader
            group_members.append(
                cast(str, self._get_entity_id_from_jid(self._remote_leader.jid))
            )

            # Add self
            group_members.append(
                cast(str, self._get_entity_id_from_jid(self._beolink_jid))
            )

            self._beolink_attribute["beolink"]["leader"] = {
                self._remote_leader.friendly_name: self._remote_leader.jid,
            }

        # If not listener, check if leader.
        else:
            beolink_listeners = await self._client.get_beolink_listeners()

            # Check if the device is a leader.
            if len(beolink_listeners) > 0:
                # Add self
                group_members.append(
                    cast(str, self._get_entity_id_from_jid(self._beolink_jid))
                )

                # Get the friendly names for the listeners from the peers
                beolink_listeners_attribute = {}
                for beolink_listener in beolink_listeners:
                    group_members.append(
                        cast(str, self._get_entity_id_from_jid(beolink_listener.jid))
                    )
                    for peer in peers:
                        if peer.jid == beolink_listener.jid:
                            beolink_listeners_attribute[peer.friendly_name] = (
                                beolink_listener.jid
                            )
                            break

                self._beolink_attribute["beolink"]["listeners"] = (
                    beolink_listeners_attribute
                )

        self._attr_group_members = group_members

        if should_update:
            self.async_write_ha_state()

    def _get_entity_id_from_jid(self, jid: str) -> str | None:
        """Get entity_id from Beolink JID (if available)."""

        unique_id = jid.split(".")[2].split("@")[0]

        entity_registry = er.async_get(self.hass)
        return entity_registry.async_get_entity_id(
            Platform.MEDIA_PLAYER, DOMAIN, unique_id
        )

    def _get_beolink_jid(self, entity_id: str) -> str | None:
        """Get beolink JID from entity_id."""
        jid = None

        entity_registry = er.async_get(self.hass)

        entity_entry = entity_registry.async_get(entity_id)
        if entity_entry:
            config_entry = cast(
                ConfigEntry,
                self.hass.config_entries.async_get_entry(
                    cast(str, entity_entry.config_entry_id)
                ),
            )

            with contextlib.suppress(KeyError):
                jid = cast(str, config_entry.data[CONF_BEOLINK_JID])

        return jid

    @property
    def state(self) -> MediaPlayerState:
        """Return the current state of the media player."""
        return BANG_OLUFSEN_STATES[self._state]

    @property
    def volume_level(self) -> float | None:
        """Volume level of the media player (0..1)."""
        if self._volume.level and self._volume.level.level:
            return float(self._volume.level.level / 100)
        return None

    @property
    def is_volume_muted(self) -> bool | None:
        """Boolean if volume is currently muted."""
        if self._volume.muted and self._volume.muted.muted:
            return self._volume.muted.muted
        return None

    @property
    def media_content_type(self) -> str:
        """Return the current media type."""
        # Hard to determine content type
        if self.source == BangOlufsenSource.URI_STREAMER:
            return MediaType.URL
        return MediaType.MUSIC

    @property
    def media_duration(self) -> int | None:
        """Return the total duration of the current track in seconds."""
        return self._playback_metadata.total_duration_seconds

    @property
    def media_position(self) -> int | None:
        """Return the current playback progress."""
        # Don't show progress if the the device is a Beolink listener.
        if self._remote_leader is None:
            return None
        return self._playback_progress.progress

    @property
    def media_image_url(self) -> str | None:
        """Return URL of the currently playing music."""
        if self._media_image:
            return self._media_image.url
        return None

    @property
    def media_image_remotely_accessible(self) -> bool:
        """Return whether or not the image of the current media is available outside the local network."""
        return not self._media_image.has_local_image

    @property
    def media_title(self) -> str | None:
        """Return the currently playing title."""
        return self._playback_metadata.title

    @property
    def media_album_name(self) -> str | None:
        """Return the currently playing album name."""
        return self._playback_metadata.album_name

    @property
    def media_album_artist(self) -> str | None:
        """Return the currently playing artist name."""
        return self._playback_metadata.artist_name

    @property
    def media_track(self) -> int | None:
        """Return the currently playing track."""
        return self._playback_metadata.track

    @property
    def media_channel(self) -> str | None:
        """Return the currently playing channel."""
        return self._playback_metadata.organization

    @property
    def source(self) -> str | None:
        """Return the current audio source."""

        # Try to fix some of the source_change chromecast weirdness.
        if hasattr(self._playback_metadata, "title"):
            # source_change is chromecast but line in is selected.
            if self._playback_metadata.title == BangOlufsenSource.LINE_IN:
                return BangOlufsenSource.LINE_IN

            # source_change is chromecast but bluetooth is selected.
            if self._playback_metadata.title == BangOlufsenSource.BLUETOOTH:
                return BangOlufsenSource.BLUETOOTH

            # source_change is line in, bluetooth or optical but stale metadata is sent through the WebSocket,
            # And the source has not changed.
            if self._source_change.id in (
                BangOlufsenSource.BLUETOOTH,
                BangOlufsenSource.LINE_IN,
                BangOlufsenSource.SPDIF,
            ):
                return BangOlufsenSource.CHROMECAST

        # source_change is chromecast and there is metadata but no artwork. Bluetooth does support metadata but not artwork
        # So i assume that it is bluetooth and not chromecast
        if (
            hasattr(self._playback_metadata, "art")
            and self._playback_metadata.art is not None
        ):
            if (
                len(self._playback_metadata.art) == 0
                and self._source_change.name == BangOlufsenSource.BLUETOOTH
            ):
                return BangOlufsenSource.BLUETOOTH

        return self._source_change.name

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return information that is not returned anywhere else."""
        attributes: dict[str, Any] = {}

        # Add Beolink attributes
        if self._beolink_attribute:
            attributes.update(self._beolink_attribute)

        return attributes

    async def async_turn_off(self) -> None:
        """Set the device to "networkStandby"."""
        await self._client.post_standby()

    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level, range 0..1."""
        await self._client.set_current_volume_level(
            volume_level=VolumeLevel(level=int(volume * 100))
        )

    async def async_mute_volume(self, mute: bool) -> None:
        """Mute or unmute media player."""
        await self._client.set_volume_mute(volume_mute=VolumeMute(muted=mute))

    async def async_media_play_pause(self) -> None:
        """Toggle play/pause media player."""
        if self.state == MediaPlayerState.PLAYING:
            await self.async_media_pause()
        elif self.state in (MediaPlayerState.PAUSED, MediaPlayerState.IDLE):
            await self.async_media_play()

    async def async_media_pause(self) -> None:
        """Pause media player."""
        await self._client.post_playback_command(command="pause")

    async def async_media_play(self) -> None:
        """Play media player."""
        await self._client.post_playback_command(command="play")

    async def async_media_stop(self) -> None:
        """Pause media player."""
        await self._client.post_playback_command(command="stop")

    async def async_media_next_track(self) -> None:
        """Send the next track command."""
        await self._client.post_playback_command(command="skip")

    async def async_media_seek(self, position: float) -> None:
        """Seek to position in ms."""
        if self.source == BangOlufsenSource.DEEZER:
            await self._client.seek_to_position(position_ms=int(position * 1000))
            # Try to prevent the playback progress from bouncing in the UI.
            self._attr_media_position_updated_at = utcnow()
            self._playback_progress = PlaybackProgress(progress=int(position))

            self.async_write_ha_state()
        else:
            _LOGGER.error("Seeking is currently only supported when using Deezer")

    async def async_media_previous_track(self) -> None:
        """Send the previous track command."""
        await self._client.post_playback_command(command="prev")

    async def async_clear_playlist(self) -> None:
        """Clear the current playback queue."""
        await self._client.post_clear_queue()

    async def async_select_source(self, source: str) -> None:
        """Select an input source."""
        if source not in self._sources.values():
            _LOGGER.error(
                "Invalid source: %s. Valid sources are: %s",
                source,
                list(self._sources.values()),
            )
            return

        key = [x for x in self._sources if self._sources[x] == source][0]

        # Check for source type
        if source in self._audio_sources.values():
            # Audio
            await self._client.set_active_source(source_id=key)
        else:
            # Video
            await self._client.post_remote_trigger(id=key)

    async def async_play_media(
        self,
        media_type: MediaType | str,
        media_id: str,
        **kwargs: Any,
    ) -> None:
        """Play from: netradio station id, URI, favourite or Deezer."""

        # Convert audio/mpeg, audio/aac etc. to MediaType.MUSIC
        if media_type.startswith("audio/"):
            media_type = MediaType.MUSIC

        if media_type not in VALID_MEDIA_TYPES:
            _LOGGER.error(
                "%s is an invalid type. Valid values are: %s",
                media_type,
                VALID_MEDIA_TYPES,
            )
            return

        if media_source.is_media_source_id(media_id):
            sourced_media = await media_source.async_resolve_media(
                self.hass, media_id, self.entity_id
            )

            media_id = async_process_play_media_url(self.hass, sourced_media.url)

            # Remove playlist extension as it is unsupported.
            if media_id.endswith(".m3u"):
                media_id = media_id.replace(".m3u", "")

        if media_type in (MediaType.URL, MediaType.MUSIC):
            await self._client.post_uri_source(uri=Uri(location=media_id))

        # The "provider" media_type may not be suitable for overlay all the time.
        # Use it for now.
        elif media_type == BangOlufsenMediaType.TTS:
            await self._client.post_overlay_play(
                overlay_play_request=OverlayPlayRequest(
                    uri=Uri(location=media_id),
                )
            )

        elif media_type == BangOlufsenMediaType.RADIO:
            await self._client.run_provided_scene(
                scene_properties=SceneProperties(
                    action_list=[
                        Action(
                            type="radio",
                            radio_station_id=media_id,
                        )
                    ]
                )
            )

        elif media_type == BangOlufsenMediaType.FAVOURITE:
            await self._client.activate_preset(id=int(media_id))

        elif media_type == BangOlufsenMediaType.DEEZER:
            try:
                if media_id == "flow":
                    deezer_id = None

                    if "id" in kwargs[ATTR_MEDIA_EXTRA]:
                        deezer_id = kwargs[ATTR_MEDIA_EXTRA]["id"]

                    # Play Deezer flow.
                    await self._client.start_deezer_flow(
                        user_flow=UserFlow(user_id=deezer_id)
                    )

                # Play a Deezer playlist or album.
                elif any(match in media_id for match in ("playlist", "album")):
                    start_from = 0
                    if "start_from" in kwargs[ATTR_MEDIA_EXTRA]:
                        start_from = kwargs[ATTR_MEDIA_EXTRA]["start_from"]

                    await self._client.add_to_queue(
                        play_queue_item=PlayQueueItem(
                            provider=PlayQueueItemType(value="deezer"),
                            start_now_from_position=start_from,
                            type="playlist",
                            uri=media_id,
                        )
                    )

                # Play a Deezer track.
                else:
                    await self._client.add_to_queue(
                        play_queue_item=PlayQueueItem(
                            provider=PlayQueueItemType(value="deezer"),
                            start_now_from_position=0,
                            type="track",
                            uri=media_id,
                        )
                    )

            except ApiException as error:
                _LOGGER.error(json.loads(error.body)["message"])

    async def async_browse_media(
        self,
        media_content_type: MediaType | str | None = None,
        media_content_id: str | None = None,
    ) -> BrowseMedia:
        """Implement the WebSocket media browsing helper."""
        return await media_source.async_browse_media(
            self.hass,
            media_content_id,
            content_filter=lambda item: item.media_content_type.startswith("audio/"),
        )

    async def async_join_players(self, group_members: list[str]) -> None:
        """Create a Beolink session with defined group members."""

        # Use the touch to join if no entities have been defined
        if len(group_members) == 0:
            await self.async_beolink_join()
            return

        jids = []
        # Get JID for each group member
        for group_member in group_members:
            jid = self._get_beolink_jid(group_member)

            # Invalid entity
            if jid is None:
                _LOGGER.warning("Error adding %s to group", group_member)
                continue

            jids.append(jid)

        await self.async_beolink_expand(jids)

    async def async_unjoin_player(self) -> None:
        """Unjoin Beolink session. End session if leader."""
        await self.async_beolink_leave()

    # Custom services:
    async def async_beolink_join(
        self, beolink_jid: str | None = None
    ) -> ServiceResponse:
        """Join a Beolink multi-room experience."""
        if beolink_jid is None:
            response = await self._client.join_latest_beolink_experience()
        else:
            response = await self._client.join_beolink_peer(jid=beolink_jid)

        if response:
            return response.dict(by_alias=True, exclude={}, exclude_none=True)
        return None

    async def async_beolink_expand(
        self, beolink_jids: list[str] | None = None, all_discovered: bool = False
    ) -> ServiceResponse:
        """Expand a Beolink multi-room experience with a device or devices."""
        response: dict[str, Any] = {"not_on_network": []}

        # Ensure that the current source is expandable
        if not self._beolink_sources[cast(str, self._source_change.id)]:
            return {"invalid_source": self.source}

        # Expand to all discovered devices
        if all_discovered:
            peers = await self._client.get_beolink_peers()

            for peer in peers:
                await self._client.post_beolink_expand(jid=peer.jid)

        # Try to expand to all defined devices
        elif beolink_jids:
            for beolink_jid in beolink_jids:
                try:
                    await self._client.post_beolink_expand(jid=beolink_jid)
                except NotFoundException:
                    response["not_on_network"].append(beolink_jid)

            if len(response["not_on_network"]) > 0:
                return response

        return None

    async def async_beolink_unexpand(self, beolink_jids: list[str]) -> None:
        """Unexpand a Beolink multi-room experience with a device or devices."""
        # Unexpand all defined devices
        for beolink_jid in beolink_jids:
            await self._client.post_beolink_unexpand(jid=beolink_jid)

    async def async_beolink_leave(self) -> None:
        """Leave the current Beolink experience."""
        await self._client.post_beolink_leave()

    async def async_beolink_allstandby(self) -> None:
        """Set all connected Beolink devices to standby."""
        await self._client.post_beolink_allstandby()
