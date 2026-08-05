# SPDX-License-Identifier: GPL-3.0-or-later
"""Minimal Blender-side bridge for Harness Blender V0.

The network worker never calls bpy. It queues trusted harness-generated code,
and a Blender timer executes that code on Blender's main thread.
"""

from __future__ import annotations

import contextlib
import io
import json
import queue
import socket
import threading
import traceback
from dataclasses import dataclass, field
from typing import Any

import bpy
from bpy.props import BoolProperty, IntProperty, StringProperty

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9876
DEFAULT_TOKEN = "harness-v0-local"
DELIMITER = b"\0"
MAX_REQUEST_BYTES = 10 * 1024 * 1024
REQUEST_TIMEOUT = 180.0
TIMER_INTERVAL = 0.05


@dataclass
class _PendingRequest:
    code: str
    strict_json: bool
    done: threading.Event = field(default_factory=threading.Event)
    response: dict[str, Any] | None = None


class _State:
    socket: socket.socket | None = None
    thread: threading.Thread | None = None
    stop_event = threading.Event()
    requests: queue.Queue[_PendingRequest] = queue.Queue()
    token: str = DEFAULT_TOKEN
    use_log: bool = False
    last_error: str = ""


def _encode(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, default=repr).encode("utf-8") + DELIMITER


def _receive(conn: socket.socket) -> dict[str, Any]:
    buffer = bytearray()
    while DELIMITER not in buffer:
        chunk = conn.recv(8192)
        if not chunk:
            raise ConnectionError("Client disconnected before completing the request")
        buffer.extend(chunk)
        if len(buffer) > MAX_REQUEST_BYTES:
            raise ValueError("Request exceeds the 10 MiB limit")
    value = json.loads(bytes(buffer[: buffer.index(DELIMITER)]).decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Request must be a JSON object")
    return value


def _execute_on_main_thread(item: _PendingRequest) -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()
    namespace: dict[str, Any] = {"result": {}}
    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exec(item.code, namespace)  # noqa: S102 - only trusted external templates reach V0
        result = namespace.get("result", {})
        if not isinstance(result, dict):
            raise TypeError("The generated tool must assign a dict to result")
        if item.strict_json:
            json.dumps(result)
        else:
            result = json.loads(json.dumps(result, default=repr))
        response: dict[str, Any] = {"status": "ok", "result": result}
    except Exception:
        response = {"status": "error", "message": traceback.format_exc()}

    if stdout.getvalue():
        response["stdout"] = stdout.getvalue()
    if stderr.getvalue():
        response["stderr"] = stderr.getvalue()
    item.response = response
    item.done.set()


def _timer_poll() -> float | None:
    if _State.socket is None:
        return None
    processed = 0
    while processed < 4:
        try:
            item = _State.requests.get_nowait()
        except queue.Empty:
            break
        _execute_on_main_thread(item)
        processed += 1
    return TIMER_INTERVAL


def _handle_client(conn: socket.socket) -> None:
    with conn:
        conn.settimeout(REQUEST_TIMEOUT)
        try:
            request = _receive(conn)
            if request.get("token") != _State.token:
                raise PermissionError("Invalid Harness Blender bridge token")
            if request.get("type") != "execute":
                raise ValueError(f"Unknown request type: {request.get('type')!r}")
            code = request.get("code")
            strict_json = request.get("strict_json")
            if not isinstance(code, str) or not isinstance(strict_json, bool):
                raise TypeError("execute requires string code and boolean strict_json")
            item = _PendingRequest(code=code, strict_json=strict_json)
            _State.requests.put(item)
            if not item.done.wait(REQUEST_TIMEOUT):
                raise TimeoutError("Blender did not process the request before timeout")
            conn.sendall(_encode(item.response or {"status": "error", "message": "Empty response"}))
        except Exception:
            try:
                conn.sendall(_encode({"status": "error", "message": traceback.format_exc()}))
            except OSError:
                pass


def _server_loop() -> None:
    sock = _State.socket
    if sock is None:
        return
    while not _State.stop_event.is_set():
        try:
            conn, _addr = sock.accept()
        except socket.timeout:
            continue
        except OSError:
            break
        _handle_client(conn)


def start_server(host: str, port: int, token: str, use_log: bool = False) -> None:
    if _State.socket is not None:
        raise RuntimeError("Harness Blender bridge is already running")
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("V0 only permits loopback hosts")
    if not token:
        raise ValueError("Access token cannot be empty")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.settimeout(0.5)
    sock.bind((host, port))
    sock.listen(5)

    _State.socket = sock
    _State.token = token
    _State.use_log = use_log
    _State.last_error = ""
    _State.stop_event.clear()
    _State.thread = threading.Thread(target=_server_loop, name="HarnessBlenderBridge", daemon=True)
    _State.thread.start()
    if not bpy.app.timers.is_registered(_timer_poll):
        bpy.app.timers.register(_timer_poll, first_interval=TIMER_INTERVAL, persistent=True)


def stop_server() -> None:
    sock = _State.socket
    _State.socket = None
    _State.stop_event.set()
    if sock is not None:
        try:
            sock.close()
        except OSError:
            pass
    thread = _State.thread
    _State.thread = None
    if thread is not None and thread.is_alive():
        thread.join(timeout=1.0)
    while True:
        try:
            item = _State.requests.get_nowait()
        except queue.Empty:
            break
        item.response = {"status": "error", "message": "Bridge stopped"}
        item.done.set()
    if bpy.app.timers.is_registered(_timer_poll):
        bpy.app.timers.unregister(_timer_poll)


class HarnessBlenderPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    host: StringProperty(name="Host", default=DEFAULT_HOST)
    port: IntProperty(name="Port", default=DEFAULT_PORT, min=1024, max=65535)
    token: StringProperty(
        name="Access Token",
        description="Must match BLENDER_TOKEN in the external MCP server",
        default=DEFAULT_TOKEN,
        subtype="PASSWORD",
    )
    auto_start: BoolProperty(name="Auto Start", default=True)
    use_log: BoolProperty(name="Log Requests", default=False)

    def draw(self, _context: bpy.types.Context) -> None:
        layout = self.layout
        layout.prop(self, "host")
        layout.prop(self, "port")
        layout.prop(self, "token")
        layout.prop(self, "auto_start")
        layout.prop(self, "use_log")
        if _State.socket is None:
            layout.operator("harness_blender.start_bridge", icon="PLAY")
            layout.label(text="Bridge stopped", icon="X")
        else:
            layout.operator("harness_blender.stop_bridge", icon="CANCEL")
            layout.label(text="Bridge running", icon="CHECKMARK")
        if _State.last_error:
            layout.label(text=_State.last_error, icon="ERROR")


class HARNESS_BLENDER_OT_start(bpy.types.Operator):
    bl_idname = "harness_blender.start_bridge"
    bl_label = "Start Harness Blender Bridge"

    def execute(self, context: bpy.types.Context) -> set[str]:
        prefs = context.preferences.addons[__package__].preferences
        try:
            start_server(prefs.host, prefs.port, prefs.token, prefs.use_log)
        except Exception as exc:
            _State.last_error = str(exc)
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, f"Bridge listening on {prefs.host}:{prefs.port}")
        return {"FINISHED"}


class HARNESS_BLENDER_OT_stop(bpy.types.Operator):
    bl_idname = "harness_blender.stop_bridge"
    bl_label = "Stop Harness Blender Bridge"

    def execute(self, _context: bpy.types.Context) -> set[str]:
        stop_server()
        self.report({"INFO"}, "Harness Blender bridge stopped")
        return {"FINISHED"}


def _auto_start() -> None:
    try:
        prefs = bpy.context.preferences.addons[__package__].preferences
        if prefs.auto_start and _State.socket is None:
            start_server(prefs.host, prefs.port, prefs.token, prefs.use_log)
    except Exception as exc:
        _State.last_error = str(exc)


_CLASSES = (
    HarnessBlenderPreferences,
    HARNESS_BLENDER_OT_start,
    HARNESS_BLENDER_OT_stop,
)


def register() -> None:
    for cls in _CLASSES:
        bpy.utils.register_class(cls)
    if not bpy.app.background:
        bpy.app.timers.register(_auto_start, first_interval=1.0)


def unregister() -> None:
    stop_server()
    if bpy.app.timers.is_registered(_auto_start):
        bpy.app.timers.unregister(_auto_start)
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
