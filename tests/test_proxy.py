import asyncio

from fragments.lsp.proxy import _encode_message, _pipe, _read_message


def make_reader(*messages: dict) -> asyncio.StreamReader:
    reader = asyncio.StreamReader()
    for msg in messages:
        reader.feed_data(_encode_message(msg))
    reader.feed_eof()
    return reader


async def collect_pipe(handler, *messages: dict) -> list[dict]:
    received = []

    async def write(data: bytes) -> None:
        r = asyncio.StreamReader()
        r.feed_data(data)
        r.feed_eof()
        received.append(await _read_message(r))

    await _pipe(make_reader(*messages), write, handler)
    return received


def test_encode_decode_roundtrip():
    msg = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}

    async def _test():
        return await _read_message(make_reader(msg))

    assert asyncio.run(_test()) == msg


def test_read_message_eof():
    async def _test():
        reader = asyncio.StreamReader()
        reader.feed_eof()
        return await _read_message(reader)

    assert asyncio.run(_test()) is None


def test_pipe_passthrough():
    msgs = [{"jsonrpc": "2.0", "method": "a"}, {"jsonrpc": "2.0", "method": "b"}]

    async def handler(msg: dict) -> dict:
        return msg

    result = asyncio.run(collect_pipe(handler, *msgs))
    assert result == msgs


def test_pipe_drops_none():
    msgs = [{"jsonrpc": "2.0", "method": "keep"}, {"jsonrpc": "2.0", "method": "drop"}]

    async def handler(msg: dict) -> dict | None:
        return None if msg["method"] == "drop" else msg

    result = asyncio.run(collect_pipe(handler, *msgs))
    assert result == [{"jsonrpc": "2.0", "method": "keep"}]


def test_pipe_transforms():
    msgs = [{"jsonrpc": "2.0", "method": "original"}]

    async def handler(msg: dict) -> dict:
        return {**msg, "method": "transformed"}

    result = asyncio.run(collect_pipe(handler, *msgs))
    assert result == [{"jsonrpc": "2.0", "method": "transformed"}]
