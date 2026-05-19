from asyncio.streams import StreamReader
from asyncio.transports import WriteTransport
from lsprotocol.types import MESSAGE_TYPES
from cattrs.converters import Converter
import asyncio
import os
import sys
from asyncio.subprocess import Process
from typing import Any, Callable
from lsprotocol.converters import get_converter
from fragments.lsp.message_queue import MessageQueue

_CONVERTER: Converter = get_converter()
_PYRIGHT_PROCESS: Process | None = None
_PYRIGHT: "MessageQueue | None" = None
_PYRIGHT_HANDLERS: dict[str, Callable[[MESSAGE_TYPES], Any]] = {}
_PROXY: "MessageQueue | None" = None
_PROXY_HANDLERS: dict[str, Callable[[MESSAGE_TYPES], Any]] = {}


def pyright() -> MessageQueue:
    global _PYRIGHT
    assert _PYRIGHT is not None
    return _PYRIGHT


def proxy() -> MessageQueue:
    global _PROXY
    assert _PROXY is not None
    return _PROXY


async def start() -> None:
    global _PYRIGHT_PROCESS, _PYRIGHT, _PROXY

    loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()

    reader: asyncio.StreamReader = asyncio.StreamReader()
    await loop.connect_read_pipe(lambda: asyncio.StreamReaderProtocol(reader), sys.stdin.buffer)
    stdin: StreamReader = reader
    transport, _ = await loop.connect_write_pipe(lambda: asyncio.BaseProtocol(), sys.stdout.buffer)
    stdout: WriteTransport = transport
    _PROXY = MessageQueue(stdin, stdout, _PROXY_HANDLERS)

    bin_directory: str = os.path.dirname(sys.executable)
    environment: dict[str, str] = dict[str, str](os.environ)
    if sys.prefix != sys.base_prefix:
        environment["VIRTUAL_ENV"] = sys.prefix

    _PYRIGHT_PROCESS = await asyncio.create_subprocess_exec(
        os.path.join(bin_directory, "basedpyright-langserver"),
        "--stdio",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=sys.stderr.buffer,
        env=environment,
    )
    pyright_stdin = _PYRIGHT_PROCESS.stdin
    pyright_stdout = _PYRIGHT_PROCESS.stdout
    assert pyright_stdin is not None
    assert pyright_stdout is not None

    _PYRIGHT = MessageQueue(pyright_stdout, pyright_stdin, _PYRIGHT_HANDLERS)

    await asyncio.gather(
        _PYRIGHT.read_loop(),
        _PROXY.read_loop(),
    )


def handle_from_client(method: str) -> Callable:
    """Register a function to handle messages from the client."""

    def decorator(func: Callable[[MESSAGE_TYPES], Any]) -> Callable[[MESSAGE_TYPES], Any]:
        _PROXY_HANDLERS[method] = func
        return func

    return decorator


def handle_from_pyright(method: str) -> Callable:
    """Register a function to handle messages from pyright."""

    def decorator(func: Callable[[MESSAGE_TYPES], Any]) -> Callable[[MESSAGE_TYPES], Any]:
        _PYRIGHT_HANDLERS[method] = func
        return func

    return decorator
