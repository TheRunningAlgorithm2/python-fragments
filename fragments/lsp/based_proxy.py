from asyncio.streams import StreamReader
from asyncio.transports import WriteTransport
import asyncio
import os
import sys
from asyncio.subprocess import Process
from typing import Callable
from lsprotocol import types
from fragments.lsp.file_state import FileState
from fragments.lsp.message_queue import MessageQueue
from fragments.lsp.types import HandlerFunc

_PYRIGHT_PROCESS: Process | None = None
_PYRIGHT: "MessageQueue | None" = None
_PYRIGHT_HANDLERS: dict[str, HandlerFunc] = {}
_PROXY: "MessageQueue | None" = None
_PROXY_HANDLERS: dict[str, HandlerFunc] = {}

FILE_STATES: dict[str, FileState] = {}
PARSE_ERRORS: dict[str, types.Diagnostic | None] = {}


def pyright() -> MessageQueue:
    global _PYRIGHT
    assert _PYRIGHT is not None
    return _PYRIGHT


def proxy() -> MessageQueue:
    global _PROXY
    assert _PROXY is not None
    return _PROXY


def handle_from_client(method: str) -> Callable[[HandlerFunc], HandlerFunc]:
    """Register a function to handle messages from the client."""

    def decorator(func: HandlerFunc) -> HandlerFunc:
        _PROXY_HANDLERS[method] = func
        return func

    return decorator


def handle_from_pyright(method: str) -> Callable[[HandlerFunc], HandlerFunc]:
    """Register a function to handle messages from pyright."""

    def decorator(func: HandlerFunc) -> HandlerFunc:
        _PYRIGHT_HANDLERS[method] = func
        return func

    return decorator


async def stop() -> None:
    global _PYRIGHT_PROCESS
    if _PYRIGHT_PROCESS is None:
        return

    _PYRIGHT_PROCESS.terminate()
    try:
        await asyncio.wait_for(_PYRIGHT_PROCESS.wait(), timeout=5.0)
    except asyncio.TimeoutError:
        _PYRIGHT_PROCESS.kill()
    _PYRIGHT_PROCESS = None


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

    pyright_task = asyncio.create_task(_PYRIGHT.read_loop())
    await _PROXY.read_loop()
    await stop()
    pyright_task.cancel()


def main() -> None:
    import asyncio
    from fragments.lsp.client_message_handlers import (  # noqa: F401
        completion,
        definition,
        diagnostics,
        document_highlight,
        document_symbols,
        folding_range,
        hover,
        inlay_hints,
        lifecycle,
        references,
        rename,
        semantic_tokens,
        signature_help,
        code_actions,
    )
    from fragments.lsp.pyright_notification_handlers import (  # noqa: F401
        capability,
        configuration,
        diagnostics as pyright_diagnostics,
    )

    asyncio.run(start())
