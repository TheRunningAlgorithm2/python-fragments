import json
import subprocess
import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable

from cattrs import Converter


@dataclass
class _PyrightResponse:
    headers: dict[str, str]
    body: dict[str, Any]


_pyright = subprocess.Popen(
    ["pyright-langserver", "--stdio"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=open("/tmp/pyright.log", "w+"),
)

_last_id = 0
_responses: dict[int, _PyrightResponse] = {}
_notification_listeners: dict[str, list[Callable[[_PyrightResponse], None]]] = defaultdict(list)
_debug_listeners: list[Callable[[_PyrightResponse], None]] = []


def _handle_response() -> None:
    assert _pyright.stdout is not None
    headers: dict[str, str] = {}
    line = _pyright.stdout.readline()
    while line != b"\r\n":
        assert b": " in line, line
        key, value = line.split(b": ", 1)
        headers[key.decode("utf-8").strip().lower()] = value.decode("utf-8").strip()
        line = _pyright.stdout.readline()

    assert "content-length" in headers
    content_length = int(headers["content-length"])
    body = json.loads(_pyright.stdout.read(content_length))

    for listener in _debug_listeners:
        listener(_PyrightResponse(headers, body))
    if "id" in body:
        _responses[body["id"]] = _PyrightResponse(headers, body)
    else:
        assert "method" in body
        for listener in _notification_listeners[body["method"]]:
            listener(_PyrightResponse(headers, body))


def _handle_outputs() -> None:
    while True:
        _handle_response()


_handle_outputs_thread = threading.Thread(target=_handle_outputs)
_handle_outputs_thread.start()


def send(data: dict[str, Any], converter: Converter, timeout: float = 10, send_id: bool = True) -> _PyrightResponse:
    assert _pyright.stdin is not None
    global _last_id
    request_id = _last_id + 1
    _last_id = request_id

    if "params" in data:
        data["params"] = converter.unstructure(data["params"])

    request_body = json.dumps({"jsonrpc": "2.0", "id": request_id, **data}).encode("utf-8")
    content_length = len(request_body)

    _pyright.stdin.write(f"Content-Length: {content_length}\r\n\r\n".encode("utf-8"))
    _pyright.stdin.write(request_body)
    _pyright.stdin.flush()

    start_time = time.time()
    while True:
        if request_id in _responses:
            response = _responses.pop(request_id)
            return response
        if time.time() - start_time > timeout:
            method = data["method"]
            raise TimeoutError(f"Request {method} timed out after {timeout} seconds - ids in responses: {_responses.keys()}")


def send_notification(data: dict[str, Any], converter: Converter, timeout: float = 10) -> None:
    assert _pyright.stdin is not None

    if "params" in data:
        data["params"] = converter.unstructure(data["params"])

    request_body = json.dumps({"jsonrpc": "2.0", "method": data["method"], **data}).encode("utf-8")
    content_length = len(request_body)

    _pyright.stdin.write(f"Content-Length: {content_length}\r\n\r\n".encode("utf-8"))
    _pyright.stdin.write(request_body)
    _pyright.stdin.flush()


def listener(method: str):
    def _listener(func: Callable[[_PyrightResponse], None]) -> Callable[[_PyrightResponse], None]:
        _notification_listeners[method].append(func)
        return func

    return _listener


def debug_listener(func: Callable[[_PyrightResponse], None]) -> Callable[[_PyrightResponse], None]:
    _debug_listeners.append(func)
    return func
