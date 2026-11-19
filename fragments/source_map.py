import bisect
from dataclasses import dataclass, field


@dataclass(slots=True)
class Segment:
    """A run of characters copied verbatim from the source into the transpiled code."""

    source_start: int
    transpiled_start: int
    length: int

    @property
    def source_end(self) -> int:
        return self.source_start + self.length

    @property
    def transpiled_end(self) -> int:
        return self.transpiled_start + self.length


@dataclass(slots=True)
class SourceMap:
    """Translate offsets between the original source and the transpiled code.

    Only offsets inside a segment can be translated - everything else is scaffolding added by the transpiler, or
    fragment syntax that has no transpiled equivalent.

    Boundary rules:
    - Segment ends are inclusive: the offset just after a segment's last character maps, so that a cursor at the
      end of an identifier (e.g. completing `obj.`) is still inside it.
    - If an offset is both the end of one segment and the start of the next, the later segment wins, since it owns
      the character at that offset.
    """

    segments: list[Segment]

    _by_source: list[Segment] = field(init=False)
    _source_starts: list[int] = field(init=False)
    _by_transpiled: list[Segment] = field(init=False)
    _transpiled_starts: list[int] = field(init=False)

    def __post_init__(self) -> None:
        # Segments are not in the same order in both files (e.g. a `for` expression is transpiled after the element
        # body it precedes in the source), so each direction needs its own sorted index.
        self._by_source = sorted(self.segments, key=lambda segment: segment.source_start)
        self._source_starts = [segment.source_start for segment in self._by_source]
        self._by_transpiled = sorted(self.segments, key=lambda segment: segment.transpiled_start)
        self._transpiled_starts = [segment.transpiled_start for segment in self._by_transpiled]

    def map_offset(self, offset: int) -> int | None:
        """Convert a source offset to its transpiled equivalent."""
        index = bisect.bisect_right(self._source_starts, offset) - 1
        if index < 0:
            return None

        segment = self._by_source[index]
        if offset > segment.source_end:
            return None

        return segment.transpiled_start + (offset - segment.source_start)

    def unmap_offset(self, offset: int) -> int | None:
        """Convert a transpiled offset back to its source equivalent."""
        index = bisect.bisect_right(self._transpiled_starts, offset) - 1
        if index < 0:
            return None

        segment = self._by_transpiled[index]
        if offset > segment.transpiled_end:
            return None

        return segment.source_start + (offset - segment.transpiled_start)
