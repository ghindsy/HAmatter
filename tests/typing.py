"""Typing helpers for Home Assistant tests."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

from aiohttp import ClientWebSocketResponse
from aiohttp.test_utils import TestClient

if TYPE_CHECKING:
    # _patcher is not available at runtime
    from unittest.mock import _patch_default_new

    # Local import to avoid processing recorder module when running a
    # testcase which does not use the recorder.
    from homeassistant.components.recorder import Recorder


class MockHAClientWebSocket(ClientWebSocketResponse):
    """Protocol for a wrapped ClientWebSocketResponse."""

    client: TestClient
    send_json_auto_id: Callable[[dict[str, Any]], Coroutine[Any, Any, None]]
    remove_device: Callable[[str, str], Coroutine[Any, Any, Any]]


type ClientSessionGenerator = Callable[..., Coroutine[Any, Any, TestClient]]
type MqttMockPahoClient = MagicMock
"""MagicMock for `paho.mqtt.client.Client`"""
type MqttMockHAClient = MagicMock
"""MagicMock for `homeassistant.components.mqtt.MQTT`."""
type MqttMockHAClientGenerator = Callable[..., Coroutine[Any, Any, MqttMockHAClient]]
"""MagicMock generator for `homeassistant.components.mqtt.MQTT`."""
type RecorderInstanceGenerator = Callable[..., Coroutine[Any, Any, Recorder]]
"""Instance generator for `homeassistant.components.recorder.Recorder`."""
type WebSocketGenerator = Callable[..., Coroutine[Any, Any, MockHAClientWebSocket]]

type Patcher = _patch_default_new
"""Type alias for unittest.mock._patcher."""
