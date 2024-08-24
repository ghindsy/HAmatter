"""Onkyo receiver."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pyeiscp

if TYPE_CHECKING:
    from .media_player import OnkyoMediaPlayer


@dataclass
class Receiver:
    """Onkyo receiver."""

    conn: pyeiscp.Connection
    model_name: str
    identifier: str
    name: str
    discovered: bool
    entities: dict[str, OnkyoMediaPlayer] = field(default_factory=dict)


@dataclass
class ReceiverInfo:
    """Onkyo receiver information."""

    host: str
    port: int
    model_name: str
    identifier: str
