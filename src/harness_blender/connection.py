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
DEFAULT_TOKEN = "harness-v0-local"


@dataclass
class BlenderConnection:
    host: str = field(default_factory=lambda: os.getenv("BLENDER_HOST", DEFAULT_HOST))
    port: int = field(default_factory=lambda: int(os.getenv("BLENDER_PORT", str(DEFAULT_PORT))))
    timeout: float = field(default_factory=lambda: float(os.getenv("BLENDER_TIMEOUT", str(DEFAULT_TIMEOUT))))
    token: str = field(default_factory=lambda: os.getenv("BLENDER_TOKEN", DEFAULT_TOKEN))
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def execute(self, code: str, *, strict_json: bool = True) -> dict[str, Any]:
        """Execute trusted harness-generated Python in Blender and return its result."""
        request = {"type": "execute", "code": code, "strict_json": strict_json, "token": self.token}
        with self._lock:
            try:
                with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
                    sock.settimeout(self.timeout)
                    sock.sendall(encode_request(request))
                    response = receive_message(sock)
            except OSError as exc:
                raise ConnectionError(
                    f"Could not reach Blender bridge at {self.host}:{self.port}. "
                    "Open Blender, enable Harness Blender Bridge, and start the server."
                ) from exc

        if response.get("status") != "ok":
            message = response.get("message", "Unknown Blender bridge error")
            stderr = response.get("stderr")
            if stderr:
                message = f"{message}\n{stderr}"
            raise RuntimeError(str(message))

        result = response.get("result", {})
        if not isinstance(result, dict):
            raise RuntimeError("Blender bridge returned a non-object result")
        return result
