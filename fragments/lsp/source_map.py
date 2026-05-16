from dataclasses import dataclass

from fragments import grammar

IMPORT_PREFIX = "from fragments.html.elements import el, sequence\n"


@dataclass
class Segment:
    orig_start: int
    orig_end: int
    trans_start: int
    trans_end: int


def to_offset(source: str, line: int, character: int) -> int:
    lines = source.split("\n")
    return sum(len(lines[line_index]) + 1 for line_index in range(line)) + character


def to_position(source: str, offset: int) -> dict:
    lines = source[:offset].split("\n")
    return {"line": len(lines) - 1, "character": len(lines[-1])}


def orig_to_trans(orig_offset: int, segments: list[Segment]) -> int | None:
    orig_cursor = 0
    trans_cursor = len(IMPORT_PREFIX)

    for segment in segments:
        gap = segment.orig_start - orig_cursor
        if orig_offset < orig_cursor + gap:
            return trans_cursor + (orig_offset - orig_cursor)
        orig_cursor += gap
        trans_cursor += gap

        fragment_orig_length = segment.orig_end - segment.orig_start
        if orig_offset < orig_cursor + fragment_orig_length:
            return None
        orig_cursor += fragment_orig_length
        trans_cursor += segment.trans_end - segment.trans_start

    return trans_cursor + (orig_offset - orig_cursor)


def trans_to_orig(trans_offset: int, segments: list[Segment]) -> int | None:
    prefix = len(IMPORT_PREFIX)
    if trans_offset < prefix:
        return None

    orig_cursor = 0
    trans_cursor = prefix

    for segment in segments:
        gap = segment.trans_start - trans_cursor
        if trans_offset < trans_cursor + gap:
            return orig_cursor + (trans_offset - trans_cursor)
        orig_cursor += gap
        trans_cursor += gap

        fragment_trans_length = segment.trans_end - segment.trans_start
        if trans_offset < trans_cursor + fragment_trans_length:
            return None
        orig_cursor += segment.orig_end - segment.orig_start
        trans_cursor += fragment_trans_length

    return orig_cursor + (trans_offset - trans_cursor)


def transpile_with_map(source: str) -> tuple[str, list[Segment]]:
    source, python = grammar.optional_regex(source, grammar.PYTHON)
    result = ""
    segments = []

    if python is not None:
        result = python

    result = IMPORT_PREFIX + result

    orig_offset = len(python) if python is not None else 0
    trans_offset = len(IMPORT_PREFIX) + (len(python) if python is not None else 0)

    while len(source) > 0:
        if source.lstrip().startswith("<>"):
            source_before_lstrip = source
            source = source.lstrip()
            whitespace = source_before_lstrip[: len(source_before_lstrip) - len(source)]

            orig_start = orig_offset + len(whitespace)
            trans_start = trans_offset + len(whitespace)

            source_before_fragment = source
            source, fragment = grammar.expect_fragment(source)
            fragment_source = source_before_fragment[: len(source_before_fragment) - len(source)]

            fragment_python = fragment.python()

            orig_end = orig_start + len(fragment_source)
            trans_end = trans_start + len(fragment_python)

            segments.append(Segment(orig_start, orig_end, trans_start, trans_end))

            result += whitespace + fragment_python
            orig_offset = orig_end
            trans_offset = trans_end
        else:
            source, python = grammar.expect_regex(source, grammar.PYTHON, "python source")
            result += python
            orig_offset += len(python)
            trans_offset += len(python)

    return result, segments
