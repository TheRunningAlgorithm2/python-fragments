from fragments import grammar
from fragments.ast_nodes import ASTFragment
from fragments.source import Source


def format_source(source_string: str) -> str:
    """Format the Python surrounding fragments, leaving the fragments untouched.

    Black cannot parse fragment syntax, so each top-level fragment is swapped for a placeholder identifier,
    the resulting plain Python is formatted with Black, and the original fragment text is then swapped back
    in verbatim. Anything inside `<>...</>`, including `{{ }}` interpolations, is never modified.

    Args:
        source_string: The full contents of a Python file that may contain fragments.

    Returns:
        The source with the surrounding Python formatted by Black and every
        fragment byte-for-byte identical to the input.

    Raises:
        RuntimeError: If black is not installed.
        grammar.ParsingError: If the source is not valid fragments syntax.
        black.InvalidInput: If the Python around the fragments is not valid.
    """
    # Black is an optional dependency (`format`), so import it lazily.
    try:
        import black
    except ImportError as error:
        raise RuntimeError(
            "Formatting requires black: pip install python-fragments[format]"
        ) from error

    _, module = grammar.expect_module(Source.from_string(source_string))

    # Choose a placeholder prefix that does not already appear in the source, so a placeholder can never be
    # confused with real code when substituting back.
    prefix = "__fragment"
    while prefix in source_string:
        prefix = "_" + prefix

    # Rebuild the file as plain Python, recording each fragment's original text (sliced from the source, so
    # it is preserved byte for byte) by placeholder name.
    fragments: dict[str, str] = {}
    parts: list[str] = []
    for child in module.children:
        if not isinstance(child, ASTFragment):
            parts.append(child.content)
            continue
        placeholder = f"{prefix}_{len(fragments)}__"
        fragments[placeholder] = source_string[child.source_start : child.source_end]
        parts.append(placeholder)

    # Format the plain Python, then put the untouched fragments back in place.
    formatted = black.format_str("".join(parts), mode=black.Mode())
    for placeholder, original in fragments.items():
        formatted = formatted.replace(placeholder, original)
    return formatted
