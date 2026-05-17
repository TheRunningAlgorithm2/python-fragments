import asyncio
import json
import os
import sys
from collections.abc import Awaitable, Callable
from typing import Any


class PyrightClient:
    def __init__(
        self,
        on_notification: Callable[[dict[str, Any]], None],
        on_request: Callable[[dict[str, Any]], Awaitable[object]] | None = None,
    ) -> None:
        self._on_notification = on_notification
        self._on_request = on_request
        self._proc: asyncio.subprocess.Process | None = None
        self._pending: dict[int | str, asyncio.Future[dict[str, Any]]] = {}
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

    async def _read(self) -> dict[str, Any] | None:
        assert self._proc and self._proc.stdout
        headers: dict[str, str] = {}
        while True:
            line = await self._proc.stdout.readline()
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
        body = await self._proc.stdout.readexactly(int(length))
        return json.loads(body)

    async def _read_once(self) -> None:
        message = await self._read()
        if message is None:
            return
        if "id" in message and "method" not in message:
            future = self._pending.pop(message["id"], None)
            if future and not future.done():
                future.set_result(message)
        elif "id" in message and "method" in message:
            _ = asyncio.ensure_future(self._handle_request(message))
        else:
            self._on_notification(message)

    async def _read_loop(self) -> None:
        try:
            while True:
                await self._read_once()
        except Exception as e:
            print(f"[pyright] {e}", file=sys.stderr, flush=True)

    async def _handle_request(self, message: dict[str, Any]) -> None:
        result = await self._on_request(message) if self._on_request else None
        self._send({"jsonrpc": "2.0", "id": message["id"], "result": result})

    async def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        assert self._proc and self._proc.stdin
        message_id = self._next_id
        self._next_id += 1
        future: asyncio.Future[dict[str, Any]] = asyncio.get_event_loop().create_future()
        self._pending[message_id] = future
        self._send({"jsonrpc": "2.0", "id": message_id, "method": method, "params": params})
        await self._proc.stdin.drain()
        return await future

    def notify(self, method: str, params: dict[str, Any]) -> None:
        self._send({"jsonrpc": "2.0", "method": method, "params": params})

    def _send(self, message: dict[str, Any]) -> None:
        assert self._proc and self._proc.stdin
        body = json.dumps(message, separators=(",", ":")).encode()
        self._proc.stdin.write(f"Content-Length: {len(body)}\r\n\r\n".encode() + body)
