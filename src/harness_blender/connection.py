"""Thread-safe connection from the external MCP server to Blender."""

from __future__ import annotations

import os
import socket
import threading
from dataclasses import dataclass, field
from typing import Any

from .protocol import encode_request, receive_message

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9876
DEFAULT_TIMEOUT = 180.0


@dataclass
class BlenderConnection:
    host: str = field(default_factory=lambda: os.getenv("BLENDER_HOST", DEFAULT_HOST))
    port: int = field(default_factory=lambda: int(os.getenv("BLENDER_PORT", str(DEFAULT_PORT))))
    timeout: float = field(default_factory=lambda: float(os.getenv("BLENDER_TIMEOUT", str(DEFAULT_TIMEOUT))))
    token: str = field(default_factory=lambda: os.getenv("BLENDER_TOKEN", ""))
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.host not in {"127.0.0.1", "localhost"}:
            raise ValueError("Harness Blender V0 only permits loopback hosts")

    def call(self, operation: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Call one semantic V0 operation in Blender."""
        if not self.token:
            raise RuntimeError(
                "BLENDER_TOKEN is not configured. Copy the generated Access Token "
                "from Blender's Harness Blender Bridge preferences."
            )
        request = {
            "type": "operation",
            "operation": operation,
            "params": params or {},
            "token": self.token,
        }
        with self._lock:
            try:
                with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
                    sock.settimeout(self.timeout)
                    sock.sendall(encode_request(request))
                    response = receive_message(sock)
            except OSError as exc:
                raise ConnectionError(
                    f"Could not reach Blender bridge at {self.host}:{self.port}. "
                    "Open Blender, enable Harness Blender Bridge, and start the bridge."
                ) from exc

        if response.get("status") != "ok":
            raise RuntimeError(str(response.get("message", "Unknown Blender bridge error")))
        result = response.get("result", {})
        if not isinstance(result, dict):
            raise RuntimeError("Blender bridge returned a non-object result")
        return result
