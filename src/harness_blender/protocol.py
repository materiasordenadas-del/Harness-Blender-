"""Null-delimited JSON protocol used by the Blender bridge."""

from __future__ import annotations

import json
import socket
from typing import Any

DELIMITER = b"\0"
MAX_RESPONSE_BYTES = 32 * 1024 * 1024


def encode_request(payload: dict[str, Any]) -> bytes:
    """Serialize one request using the bridge framing protocol."""
    return json.dumps(payload, separators=(",", ":")).encode("utf-8") + DELIMITER


def receive_message(sock: socket.socket, *, max_bytes: int = MAX_RESPONSE_BYTES) -> dict[str, Any]:
    """Read exactly one null-delimited JSON message from a socket."""
    buffer = bytearray()
    while DELIMITER not in buffer:
        chunk = sock.recv(8192)
        if not chunk:
            raise ConnectionError("Blender closed the connection before sending a complete response")
        buffer.extend(chunk)
        if len(buffer) > max_bytes:
            raise ValueError(f"Blender response exceeded {max_bytes} bytes")

    raw = bytes(buffer[: buffer.index(DELIMITER)])
    message = json.loads(raw.decode("utf-8"))
    if not isinstance(message, dict):
        raise ValueError("Blender response must be a JSON object")
    return message
