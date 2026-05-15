from dataclasses import dataclass

from fragments import grammar

IMPORT_PREFIX = "from fragments.html.elements import el, sequence\n"


@dataclass
class Segment:
    orig_start: int
    orig_end: int
    trans_start: int
    trans_end: int


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
