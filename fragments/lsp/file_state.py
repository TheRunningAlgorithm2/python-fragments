import bisect
from dataclasses import dataclass, field
from fragments.ast_nodes import ASTModule, ASTPython
from lsprotocol.types import Position, Range
from fragments import grammar
from fragments.source import Source


def _line_starts(text: str) -> list[int]:
    """Build a list of line start offsets to make lookup easier in the future."""
    return [0] + [i + 1 for i, char in enumerate(text) if char == "\n"]


def _position_to_offset(position: Position, line_starts: list[int]) -> int:
    return line_starts[position.line] + position.character


def _offset_to_position(offset: int, line_starts: list[int]) -> Position:
    line = bisect.bisect_right(line_starts, offset) - 1
    character = offset - line_starts[line]
    return Position(line=line, character=character)


@dataclass(slots=True)
class FileState:
    """Cache a transpiled file so it doesn't need to be repeatedly transpiled."""

    original: str
    transpiled: str = field(init=False)
    ast_module: ASTModule = field(init=False)
    vanilla: bool = field(init=False)
    original_line_starts: list[int] = field(init=False)
    transpiled_line_starts: list[int] = field(init=False)

    def __post_init__(self) -> None:
        source = Source.from_string(self.original)
        _, self.ast_module = grammar.expect_module(source)
        self.ast_module.transpile()
        self.transpiled = self.ast_module.transpiled_content
        self.vanilla = len(self.ast_module.children) == 1 and isinstance(self.ast_module.children[0], ASTPython)
        self.original_line_starts = _line_starts(self.original)
        self.transpiled_line_starts = _line_starts(self.transpiled)

    def map_position(self, original_position: Position) -> Position | None:
        """Convert a position to its post-transpilation equivalent."""
        original_offset = _position_to_offset(original_position, self.original_line_starts)
        mapped_offset = self.ast_module.map_offset(original_offset)
        if mapped_offset is None:
            return None
        return _offset_to_position(mapped_offset, self.transpiled_line_starts)

    def unmap_position(self, mapped_position: Position) -> Position | None:
        """Convert a post-transpilation position back to an original source position."""
        mapped_offset = _position_to_offset(mapped_position, self.transpiled_line_starts)
        original_offset = self.ast_module.unmap_offset(mapped_offset)
        if original_offset is None:
            return None
        return _offset_to_position(original_offset, self.original_line_starts)

    def map_range(self, original_range: Range) -> Range | None:
        """Convert an original source range to its post-transpilation equivalent."""
        start = self.map_position(original_range.start)
        end = self.map_position(original_range.end)
        if start is None or end is None:
            return None
        return Range(start=start, end=end)

    def unmap_range(self, mapped_range: Range) -> Range | None:
        """Convert a post-transpilation range back to an original source range."""
        start = self.unmap_position(mapped_range.start)
        end = self.unmap_position(mapped_range.end)
        if start is None or end is None:
            return None
        return Range(start=start, end=end)
