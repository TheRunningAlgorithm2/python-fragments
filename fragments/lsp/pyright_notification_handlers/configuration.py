import sys
from lsprotocol import types
from lsprotocol.types import REQUESTS, NOTIFICATIONS
from typing import cast
from fragments.lsp import based_proxy
from fragments.lsp.based_proxy import handle_from_pyright


@handle_from_pyright(types.WORKSPACE_CONFIGURATION)
async def workspace_configuration(message: REQUESTS | NOTIFICATIONS) -> None:
    request = cast(types.ConfigurationRequest, message)
    original_id = request.id
    response = cast(types.ConfigurationResponse, await based_proxy.proxy().request(request))

    if response.result is not None:
        result = list(response.result)
        for i, item in enumerate(request.params.items):
            if item.section == "python" and i < len(result):
                config = dict(result[i] or {})
                config["pythonPath"] = sys.executable
                config["defaultInterpreterPath"] = sys.executable
                result[i] = config
        response.result = result

    based_proxy.pyright().respond(original_id, response)
