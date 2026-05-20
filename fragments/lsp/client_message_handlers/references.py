from collections.abc import Sequence
from lsprotocol import types
from lsprotocol.types import REQUESTS, NOTIFICATIONS
from typing import cast
from fragments.lsp import based_proxy
from fragments.lsp.based_proxy import handle_from_client


def _remap_locations(locations: Sequence[types.Location]) -> list[types.Location]:
    remapped: list[types.Location] = []
    for location in locations:
        target_state = based_proxy.FILE_STATES.get(location.uri)
        if target_state is not None:
            new_range = target_state.unmap_range(location.range)
            if new_range is None:
                continue
            location.range = new_range
        remapped.append(location)
    return remapped


@handle_from_client(types.TEXT_DOCUMENT_REFERENCES)
async def references(message: REQUESTS | NOTIFICATIONS) -> None:
    request = cast(types.ReferencesRequest, message)
    original_id = request.id
    file_state = based_proxy.FILE_STATES.get(request.params.text_document.uri)

    if file_state is None or file_state.vanilla:
        based_proxy.proxy().respond(original_id, await based_proxy.pyright().request(request))
        return

    mapped_position = file_state.map_position(request.params.position)
    if mapped_position is None:
        based_proxy.proxy().respond(original_id, types.ReferencesResponse(id=original_id, result=None))
        return

    request.params.position = mapped_position
    response = cast(types.ReferencesResponse, await based_proxy.pyright().request(request))

    if response.result:
        response.result = _remap_locations(response.result)

    based_proxy.proxy().respond(original_id, response)


@handle_from_client(types.TEXT_DOCUMENT_TYPE_DEFINITION)
async def type_definition(message: REQUESTS | NOTIFICATIONS) -> None:
    request = cast(types.TypeDefinitionRequest, message)
    original_id = request.id
    file_state = based_proxy.FILE_STATES.get(request.params.text_document.uri)

    if file_state is None or file_state.vanilla:
        based_proxy.proxy().respond(original_id, await based_proxy.pyright().request(request))
        return

    mapped_position = file_state.map_position(request.params.position)
    if mapped_position is None:
        based_proxy.proxy().respond(original_id, types.TypeDefinitionResponse(id=original_id, result=None))
        return

    request.params.position = mapped_position
    response = cast(types.TypeDefinitionResponse, await based_proxy.pyright().request(request))

    if isinstance(response.result, list):
        response.result = _remap_locations(cast(list[types.Location], response.result))
    elif isinstance(response.result, types.Location):
        target_state = based_proxy.FILE_STATES.get(response.result.uri)
        if target_state is not None:
            new_range = target_state.unmap_range(response.result.range)
            if new_range is not None:
                response.result.range = new_range

    based_proxy.proxy().respond(original_id, response)


@handle_from_client(types.TEXT_DOCUMENT_IMPLEMENTATION)
async def implementation(message: REQUESTS | NOTIFICATIONS) -> None:
    request = cast(types.ImplementationRequest, message)
    original_id = request.id
    file_state = based_proxy.FILE_STATES.get(request.params.text_document.uri)

    if file_state is None or file_state.vanilla:
        based_proxy.proxy().respond(original_id, await based_proxy.pyright().request(request))
        return

    mapped_position = file_state.map_position(request.params.position)
    if mapped_position is None:
        based_proxy.proxy().respond(original_id, types.ImplementationResponse(id=original_id, result=None))
        return

    request.params.position = mapped_position
    response = cast(types.ImplementationResponse, await based_proxy.pyright().request(request))

    if isinstance(response.result, list):
        response.result = _remap_locations(cast(list[types.Location], response.result))
    elif isinstance(response.result, types.Location):
        target_state = based_proxy.FILE_STATES.get(response.result.uri)
        if target_state is not None:
            new_range = target_state.unmap_range(response.result.range)
            if new_range is not None:
                response.result.range = new_range

    based_proxy.proxy().respond(original_id, response)
