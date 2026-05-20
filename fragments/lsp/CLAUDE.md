# LSP Handler Patterns

## Mutate and forward

Handlers receive typed lsprotocol objects. Mutate them in place and forward directly — never reconstruct a message from its fields.

## Position-mapping handlers

Handlers that need to remap positions follow this pattern:

1. Get `file_state` from `FILE_STATES`
2. If `file_state is None or file_state.vanilla`: forward the request verbatim and respond, then early return
3. Map the request position using `file_state.map_position()` — if it returns `None` (position is inside fragment syntax), return without responding
4. Forward the mutated request to pyright
5. Unmap positions/ranges in the response using `file_state.unmap_position()` or `file_state.unmap_range()`
6. Respond to the client

See `hover.py` for the canonical example.
