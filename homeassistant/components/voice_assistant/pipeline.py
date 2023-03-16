"""Classes for voice assistant pipelines."""
from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any

from aiohttp import StreamReader

from homeassistant.components import conversation, stt
from homeassistant.core import Context, HomeAssistant

DEFAULT_TIMEOUT = 30  # seconds


@dataclass
class PipelineRequest:
    """Request to start a pipeline run."""

    stt_audio: StreamReader | None
    stt_metadata: stt.SpeechMetadata | None
    stt_text: str | None = None
    conversation_id: str | None = None


class PipelineEventType(str, Enum):
    """Event types emitted during a pipeline run."""

    RUN_START = "run-start"
    RUN_FINISH = "run-finish"
    STT_START = "stt-start"
    STT_FINISH = "stt-finish"
    INTENT_START = "intent-start"
    INTENT_FINISH = "intent-finish"
    TTS_START = "tts-start"
    TTS_FINISH = "tts-finish"
    ERROR = "error"


@dataclass
class PipelineEvent:
    """Events emitted during a pipeline run."""

    type: PipelineEventType
    data: dict[str, Any] | None = None
    timestamp: int = field(default_factory=time.monotonic_ns)

    def as_dict(self) -> dict[str, Any]:
        """Return a dict representation of the event."""
        return {"type": self.type, "timestamp": self.timestamp, "data": self.data or {}}


@dataclass
class Pipeline:
    """A voice assistant pipeline."""

    name: str
    language: str
    stt_engine: str | None
    agent_id: str | None
    tts_engine: str | None

    # output format for tts (bytes or media src url) - can be dynamic
    # get supported codecs for tts
    # raise error in get_provider
    # pcm output for azure?
    # pass in voice instead of gender
    #
    # pipeline platform?
    # output stream of events
    #
    # binary handler for websocket?
    #
    # NOTE: Use collection helper for storage
    # collection.async_add_change_set_listener(_collection_changed)
    # collection.StorageCollectionWebsocket(
    #     storage_collection, DOMAIN, DOMAIN, STORAGE_FIELDS, STORAGE_FIELDS
    # ).async_setup(hass)
    #
    # TODO: Add intent parse/executed events to conversation
    #
    # Test conversation agent timeouts, etc.
    # Cancel pipelines on unsubscribe?
    # Runtime wrapper with task

    async def run(
        self,
        hass: HomeAssistant,
        context: Context,
        request: PipelineRequest,
        event_callback: Callable[[PipelineEvent], None],
        timeout: int | float | None = DEFAULT_TIMEOUT,
    ) -> None:
        """Run a pipeline with an optional timeout."""
        await asyncio.wait_for(
            self._run(hass, context, request, event_callback), timeout=timeout
        )

    async def _run(
        self,
        hass: HomeAssistant,
        context: Context,
        request: PipelineRequest,
        event_callback: Callable[[PipelineEvent], None],
    ) -> None:
        """Run a pipeline."""
        event_callback(
            PipelineEvent(
                PipelineEventType.RUN_START,
                {
                    "pipeline": self.name,
                    "language": self.language,
                },
            )
        )

        # TODO validate that pipeline contains valid engines for STT/TTS

        stt_text = request.stt_text
        # if stt_text is None:
        #     # Run speech to text
        #     if (request.stt_audio is None) or (request.stt_metadata is None):
        #         yield PipelineEvent(
        #             PipelineEventType.ERROR,
        #             {
        #                 "code": "bad_input",
        #                 "message": "STT audio and metadata is required if text is missing",
        #             },
        #         )

        #     stt_provider = stt.async_get_provider(hass, self.stt_engine)
        #     yield PipelineEvent(
        #         PipelineEventType.STT_START, {"engine": self.stt_engine}
        #     )
        #     stt_result = await stt_provider.async_process_audio_stream(
        #         request.stt_metadata, request.stt_audio
        #     )
        #     stt_text = stt_result.text
        #     yield PipelineEvent(PipelineEventType.STT_FINISH, {"text": stt_text})

        # Run intent recognition
        if stt_text is None:
            event_callback(
                PipelineEvent(
                    PipelineEventType.ERROR,
                    {
                        "code": "speech_not_recognized",
                        "message": "no speech returned from agent",
                    },
                )
            )
            return

        event_callback(
            PipelineEvent(
                PipelineEventType.INTENT_START,
                {"agent_id": self.agent_id or "default"},
            )
        )

        conversation_result = await conversation.async_converse(
            hass=hass,
            text=stt_text,
            conversation_id=request.conversation_id,
            context=context,
            language=self.language,
            agent_id=self.agent_id,
        )

        tts_text: str | None = conversation_result.response.speech.get("plain", {}).get(
            "speech"
        )
        event_callback(
            PipelineEvent(
                PipelineEventType.INTENT_FINISH,
                {
                    "speech": tts_text,
                    "response": conversation_result.response.as_dict(),
                },
            )
        )

        # Run text to speech
        if tts_text is None:
            event_callback(
                PipelineEvent(
                    PipelineEventType.ERROR,
                    {
                        "code": "response_has_no_speech",
                        "message": "no speech returned from agent",
                    },
                )
            )
            return

        tts_url = None

        # Only output STT if we also did TTS
        # if request.stt_audio is not None:
        #     speech_manager: tts.SpeechManager = hass.data[tts.DOMAIN]
        #     yield PipelineEvent(
        #         PipelineEventType.TTS_START,
        #         {"engine": self.tts_engine},
        #     )
        #     tts_url = await speech_manager.async_get_url_path(self.tts_engine, tts_text)
        #     yield PipelineEvent(
        #         PipelineEventType.TTS_FINISH,
        #         {"url": tts_url},
        #     )

        event_callback(
            PipelineEvent(
                PipelineEventType.RUN_FINISH,
                {
                    "stt_text": stt_text,
                    "conversation_result": conversation_result,
                    "tts_url": tts_url,
                },
            )
        )
