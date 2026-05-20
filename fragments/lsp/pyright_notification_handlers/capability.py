from lsprotocol import types
from lsprotocol.types import REQUESTS, NOTIFICATIONS
from typing import cast
from fragments.lsp import based_proxy
from fragments.lsp.based_proxy import handle_from_pyright


@handle_from_pyright(types.CLIENT_REGISTER_CAPABILITY)
async def register_capability(message: REQUESTS | NOTIFICATIONS) -> None:
    request = cast(types.RegistrationRequest, message)
    original_id = request.id
    response = await based_proxy.proxy().request(request)
    based_proxy.pyright().respond(original_id, response)


@handle_from_pyright(types.CLIENT_UNREGISTER_CAPABILITY)
async def unregister_capability(message: REQUESTS | NOTIFICATIONS) -> None:
    request = cast(types.UnregistrationRequest, message)
    original_id = request.id
    response = await based_proxy.proxy().request(request)
    based_proxy.pyright().respond(original_id, response)
