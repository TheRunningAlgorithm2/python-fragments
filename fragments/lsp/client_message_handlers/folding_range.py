from lsprotocol import types
from lsprotocol.types import REQUESTS, NOTIFICATIONS
from typing import cast
from fragments.lsp import based_proxy
from fragments.lsp.based_proxy import handle_from_client


@handle_from_client(types.TEXT_DOCUMENT_FOLDING_RANGE)
async def folding_range(message: REQUESTS | NOTIFICATIONS) -> None:
    request = cast(types.FoldingRangeRequest, message)
    based_proxy.proxy().respond(request.id, cast(types.FoldingRangeResponse, await based_proxy.pyright().request(request)))
