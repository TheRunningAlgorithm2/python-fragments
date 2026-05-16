import asyncio
import json
import os
import sys
from collections.abc import Awaitable, Callable


def _encode(message: dict) -> bytes:
    body = json.dumps(message, separators=(",", ":")).encode()
    return f"Content-Length: {len(body)}\r\n\r\n".encode() + body


async def _read(reader: asyncio.StreamReader) -> dict | None:
    headers: dict[str, str] = {}
    while True:
        line = await reader.readline()
        if not line:
            return None
        line = line.decode().rstrip("\r\n")
        if not line:
            break
        key, _, value = line.partition(":")
        headers[key.strip()] = value.strip()
    length = headers.get("Content-Length")
    if length is None:
        return None
    body = await reader.readexactly(int(length))
    return json.loads(body)


class PyrightClient:
    def __init__(
        self,
        on_notification: Callable[[dict], None],
        on_request: Callable[[dict], Awaitable[object]] | None = None,
    ) -> None:
        self._on_notification = on_notification
        self._on_request = on_request
        self._proc: asyncio.subprocess.Process | None = None
        self._pending: dict[int | str, asyncio.Future[dict]] = {}
        self._next_id = 1

    async def start(self) -> None:
        bin_directory = os.path.dirname(sys.executable)
        environment = dict(os.environ)
        if sys.prefix != sys.base_prefix:
            environment["VIRTUAL_ENV"] = sys.prefix
        self._proc = await asyncio.create_subprocess_exec(
            os.path.join(bin_directory, "basedpyright-langserver"),
            "--stdio",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=sys.stderr.buffer,
            env=environment,
        )
        asyncio.create_task(self._read_loop())

    async def _read_loop(self) -> None:
        assert self._proc and self._proc.stdout
        try:
            while True:
                message = await _read(self._proc.stdout)
                if message is None:
                    break
                if "id" in message and "method" not in message:
                    # Response to one of our requests
                    future = self._pending.pop(message["id"], None)
                    if future and not future.done():
                        future.set_result(message)
                elif "id" in message and "method" in message:
                    # Server-to-client request — must respond
                    asyncio.ensure_future(self._handle_request(message))
                else:
                    self._on_notification(message)
        except Exception as e:
            print(f"[pyright] {e}", file=sys.stderr, flush=True)

    async def _handle_request(self, message: dict) -> None:
        result = await self._on_request(message) if self._on_request else None
        self._send({"jsonrpc": "2.0", "id": message["id"], "result": result})

    async def request(self, method: str, params: dict) -> dict:
        message_id = self._next_id
        self._next_id += 1
        future: asyncio.Future[dict] = asyncio.get_event_loop().create_future()
        self._pending[message_id] = future
        self._proc.stdin.write(_encode({"jsonrpc": "2.0", "id": message_id, "method": method, "params": params}))  # type: ignore[union-attr]
        await self._proc.stdin.drain()  # type: ignore[union-attr]
        return await future

    def notify(self, method: str, params: dict) -> None:
        if self._proc and self._proc.stdin:
            self._send({"jsonrpc": "2.0", "method": method, "params": params})

    def _send(self, message: dict) -> None:
        if self._proc and self._proc.stdin:
            self._proc.stdin.write(_encode(message))
