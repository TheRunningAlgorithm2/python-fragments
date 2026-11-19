from dataclasses import dataclass, field

from fragments.source_map import Segment, SourceMap


@dataclass(slots=True)
class TranspiledCodeWriter:
    """Build transpiled code piece by piece, recording where source code is copied into it.

    Offsets are tracked by the writer, never by the caller: anything written with `map` is recorded in the source map
    at wherever it actually lands in the transpiled code.
    """

    source: str

    _parts: list[str] = field(default_factory=list, init=False)
    _segments: list[Segment] = field(default_factory=list, init=False)
    _length: int = field(default=0, init=False)

    def write(self, code: str) -> None:
        """Write transpiler-generated code that has no equivalent in the source."""
        self._parts.append(code)
        self._length += len(code)

    def map(self, source_start: int, source_end: int) -> None:
        """Copy `source[source_start:source_end]` verbatim into the transpiled code and record the mapping."""
        if not 0 <= source_start <= source_end <= len(self.source):
            raise ValueError(f"Source span [{source_start}, {source_end}) is outside the source (length {len(self.source)})")

        self._segments.append(Segment(source_start, self._length, source_end - source_start))
        self.write(self.source[source_start:source_end])

    def transpiled_content(self) -> str:
        return "".join(self._parts)

    def source_map(self) -> SourceMap:
        return SourceMap(list(self._segments))
