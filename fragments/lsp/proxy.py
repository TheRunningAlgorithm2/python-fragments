import asyncio
import json
import sys
from collections.abc import Awaitable, Callable

MessageHandler = Callable[[dict], Awaitable[dict | None]]


async def _read_message(reader: asyncio.StreamReader) -> dict | None:
    headers: dict[str, str] = {}
    while True:
        line = await reader.readline()
        if not line:
            return None
        line = line.decode("utf-8").rstrip("\r\n")
        if not line:
            break
        key, _, value = line.partition(":")
        headers[key.strip()] = value.strip()
    length = int(headers["Content-Length"])
    body = await reader.readexactly(length)
    return json.loads(body)


def _encode_message(message: dict) -> bytes:
    body = json.dumps(message, separators=(",", ":")).encode("utf-8")
    return f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8") + body


async def _pipe(
    reader: asyncio.StreamReader,
    write: Callable[[bytes], Awaitable[None]],
    handler: MessageHandler,
) -> None:
    while True:
        message = await _read_message(reader)
        if message is None:
            break
        result = await handler(message)
        if result is not None:
            await write(_encode_message(result))


async def run(
    on_from_editor: MessageHandler | None = None,
    on_from_pyright: MessageHandler | None = None,
) -> None:
    async def passthrough(msg: dict) -> dict:
        return msg

    on_from_editor = on_from_editor or passthrough
    on_from_pyright = on_from_pyright or passthrough

    loop = asyncio.get_event_loop()

    editor_reader = asyncio.StreamReader()
    await loop.connect_read_pipe(lambda: asyncio.StreamReaderProtocol(editor_reader), sys.stdin.buffer)

    stdout_lock = asyncio.Lock()

    async def write_to_editor(data: bytes) -> None:
        async with stdout_lock:
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()

    pyright = await asyncio.create_subprocess_exec(
        "basedpyright-langserver",
        "--stdio",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=sys.stderr.buffer,
    )
    assert pyright.stdin is not None
    assert pyright.stdout is not None

    async def write_to_pyright(data: bytes) -> None:
        pyright.stdin.write(data)
        await pyright.stdin.drain()

    editor_to_pyright = asyncio.create_task(_pipe(editor_reader, write_to_pyright, on_from_editor))
    pyright_to_editor = asyncio.create_task(_pipe(pyright.stdout, write_to_editor, on_from_pyright))

    done, pending = await asyncio.wait(
        [editor_to_pyright, pyright_to_editor],
        return_when=asyncio.FIRST_COMPLETED,
    )
    for task in pending:
        task.cancel()


if __name__ == "__main__":
    from fragments.lsp.intercept import Interceptor
    interceptor = Interceptor()
    asyncio.run(run(on_from_editor=interceptor.on_from_editor, on_from_pyright=interceptor.on_from_pyright))
