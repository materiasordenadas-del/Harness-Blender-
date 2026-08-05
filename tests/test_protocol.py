import json
import socket
import threading

from harness_blender.protocol import DELIMITER, encode_request, receive_message


def test_encode_request_is_null_delimited_json():
    payload = {"type": "execute", "strict_json": True, "code": "result = {}"}
    encoded = encode_request(payload)
    assert encoded.endswith(DELIMITER)
    assert json.loads(encoded[:-1].decode("utf-8")) == payload


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
