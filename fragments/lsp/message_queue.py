from dataclasses import dataclass, field
from lsprotocol.types import MESSAGE_TYPES, REQUESTS, NOTIFICATIONS, RESPONSES
from cattrs.converters import Converter
import asyncio
import json
import sys
from typing import Any, Callable, Protocol
from lsprotocol.converters import get_converter
from lsprotocol import types
from typing import cast

_CONVERTER: Converter = get_converter()


class Writable(Protocol):
    def write(self, data: bytes) -> None: ...


class IDNotPendingError(Exception):
    pass


class MessageMethodNotKnownError(Exception):
    pass


@dataclass
class MessageQueue:
    reader: asyncio.StreamReader
    writer: Writable
    handlers: dict[str, Callable[[MESSAGE_TYPES], Any]]
    next_id: int = 1
    pending: dict[int | str, tuple[str, asyncio.Future[RESPONSES]]] = field(default_factory=dict)

    async def pop_message(self) -> MESSAGE_TYPES | None:
        """Pop the latest message from STDIN and turn into the correct lsprotocol type."""
        headers: dict[str, str] = {}

        while True:
            line: bytes = await self.reader.readline()
            if not line:
                return None
            decoded: str = line.decode().rstrip("\r\n")
            if not decoded:
                break
            key, value = decoded.split(":", maxsplit=1)
            headers[key.strip()] = value.strip()

        length = headers.get("Content-Length")
        if length is None:
            return None

        message_body = await self.reader.readexactly(int(length))
        message_json = json.loads(message_body)

        if "method" in message_json:
            method = message_json["method"]
            if method not in types.METHOD_TO_TYPES:
                raise MessageMethodNotKnownError(f"{method} is not known")
            message_type = types.METHOD_TO_TYPES[method][0]
        else:
            message_id = message_json["id"]
            if message_id not in self.pending:
                raise IDNotPendingError(f"{message_id} is not pending")
            message_type = types.METHOD_TO_TYPES[self.pending[message_id][0]][1]

        message: MESSAGE_TYPES = _CONVERTER.structure(message_json, message_type)
        return message

    async def read_loop(self) -> None:
        """Continuously watch the StreamReader and handle new messages."""
        while True:
            try:
                message: MESSAGE_TYPES | None = await self.pop_message()
            except (IDNotPendingError, MessageMethodNotKnownError) as e:
                sys.stderr.write(str(e) + "\n")
                continue
            if message is None:
                break

            method = getattr(message, "method", None)
            if method is not None and isinstance(method, str):
                handler = self.handlers.get(method)
                if handler is None:
                    continue
                asyncio.create_task(handler(message))
                continue

            message_id = getattr(message, "id", None)
            if message_id is not None and message_id in self.pending:
                _, future = self.pending[message_id]
                future.set_result(cast(RESPONSES, message))
                del self.pending[message_id]
                continue

    def notify(self, message: NOTIFICATIONS) -> None:
        """Send a notification (no response expected)."""
        message_json: dict[str, Any] = _CONVERTER.unstructure(message)
        message_content_bytes: bytes = json.dumps(message_json).encode()
        message_bytes: bytes = f"Content-Length: {len(message_content_bytes)}\r\n\r\n".encode() + message_content_bytes
        self.writer.write(message_bytes)

    async def request(self, message: REQUESTS) -> RESPONSES:
        """Send a request."""
        message.id = self.next_id
        message_json = _CONVERTER.unstructure(message)
        message_content_bytes: bytes = json.dumps(message_json).encode()
        message_length: int = len(message_content_bytes)
        message_bytes: bytes = f"Content-Length: {message_length}\r\n\r\n".encode() + message_content_bytes
        future: asyncio.Future[RESPONSES] = asyncio.get_running_loop().create_future()
        self.pending[self.next_id] = (message.method, future)
        self.writer.write(message_bytes)
        self.next_id += 1
        return await future
