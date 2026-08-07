import json
import socket
import threading

import pytest

from harness_blender.protocol import DELIMITER, encode_request, receive_message


def test_encode_request_is_null_delimited_json():
    payload = {
        "type": "operation",
        "operation": "ping",
        "params": {},
        "token": "example-token-not-a-default",
    }
    encoded = encode_request(payload)
    assert encoded.endswith(DELIMITER)
    assert json.loads(encoded[:-1].decode("utf-8")) == payload
    assert b'"code"' not in encoded


def test_receive_message_handles_chunked_payload():
    left, right = socket.socketpair()
    try:
        raw = json.dumps({"status": "ok", "result": {"value": 7}}).encode() + DELIMITER

        def writer():
            right.sendall(raw[:4])
            right.sendall(raw[4:])

        thread = threading.Thread(target=writer)
        thread.start()
        assert receive_message(left)["result"]["value"] == 7
        thread.join()
    finally:
        left.close()
        right.close()


def test_receive_message_enforces_size_limit():
    left, right = socket.socketpair()
    try:
        right.sendall(b'{"status":"ok","padding":"1234567890"}' + DELIMITER)
        with pytest.raises(ValueError, match="exceeded"):
            receive_message(left, max_bytes=16)
    finally:
        left.close()
        right.close()
