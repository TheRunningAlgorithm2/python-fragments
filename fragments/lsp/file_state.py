from __future__ import annotations

import bisect
from dataclasses import dataclass, field

from lsprotocol import types

from fragments.ast_nodes import ASTHTMLElement, ASTHTMLText, ASTInterpolation, ASTModule, ASTPython


def _build_line_starts(source: str) -> list[int]:
    starts = [0]
    for i, character in enumerate(source):
        if character == "\n":
            starts.append(i + 1)
    return starts


def _position_to_offset(line_starts: list[int], line: int, character: int) -> int:
    return line_starts[line] + character


def _offset_to_position(line_starts: list[int], offset: int) -> types.Position:
    line = bisect.bisect_right(line_starts, offset) - 1
    return types.Position(line=line, character=offset - line_starts[line])


@dataclass(slots=True)
class _FileState:
    original: str
    transpiled: str
    module: ASTModule
    original_line_starts: list[int] = field(init=False)
    transpiled_line_starts: list[int] = field(init=False)

    def __post_init__(self) -> None:
        self.original_line_starts = _build_line_starts(self.original)
        self.transpiled_line_starts = _build_line_starts(self.transpiled)

    def _interpolation_expression_start(self, interpolation: ASTInterpolation) -> int:
        after = self.original[interpolation.source_start + 2 :]
        return interpolation.source_start + 2 + (len(after) - len(after.lstrip()))

    def _original_offset_to_transpiled_offset(self, original_offset: int) -> int | None:
        for child in self.module.children:
            if isinstance(child, ASTPython):
                if child.source_start <= original_offset < child.source_end:
                    return child.transpiled_start + (original_offset - child.source_start)
            elif child.source_start <= original_offset < child.source_end:
                return self._original_offset_in_nodes(original_offset, child.children)
        return None

    def _original_offset_in_nodes(self, original_offset: int, nodes: list[ASTHTMLElement | ASTHTMLText | ASTInterpolation]) -> int | None:
        for node in nodes:
            if not (node.source_start <= original_offset < node.source_end):
                continue
            if isinstance(node, ASTInterpolation):
                expression_start = self._interpolation_expression_start(node)
                return node.transpiled_start + (original_offset - expression_start) if original_offset >= expression_start else None
            if isinstance(node, ASTHTMLElement):
                for interpolation in [node.if_attribute, node.for_attribute, *(a.interpolation for a in node.attributes.values())]:
                    if interpolation is not None and interpolation.source_start <= original_offset < interpolation.source_end:
                        expression_start = self._interpolation_expression_start(interpolation)
                        return interpolation.transpiled_start + (original_offset - expression_start) if original_offset >= expression_start else None
                return self._original_offset_in_nodes(original_offset, list(node.children))
        return None

    def _transpiled_offset_to_original_offset(self, transpiled_offset: int) -> int | None:
        for child in self.module.children:
            if isinstance(child, ASTPython):
                if child.transpiled_start <= transpiled_offset < child.transpiled_end:
                    return child.source_start + (transpiled_offset - child.transpiled_start)
            elif child.transpiled_start <= transpiled_offset < child.transpiled_end:
                return self._transpiled_offset_in_nodes(transpiled_offset, child.children)
        return None

    def _transpiled_offset_in_nodes(self, transpiled_offset: int, nodes: list[ASTHTMLElement | ASTHTMLText | ASTInterpolation]) -> int | None:
        for node in nodes:
            if not (node.transpiled_start <= transpiled_offset < node.transpiled_end):
                continue
            if isinstance(node, ASTInterpolation):
                return self._interpolation_expression_start(node) + (transpiled_offset - node.transpiled_start)
            if isinstance(node, ASTHTMLElement):
                for interpolation in [node.if_attribute, node.for_attribute, *(a.interpolation for a in node.attributes.values())]:
                    if interpolation is not None and interpolation.transpiled_start <= transpiled_offset < interpolation.transpiled_end:
                        return self._interpolation_expression_start(interpolation) + (transpiled_offset - interpolation.transpiled_start)
                return self._transpiled_offset_in_nodes(transpiled_offset, list(node.children))
        return None

    def original_to_transpiled_position(self, position: types.Position) -> types.Position | None:
        original_offset = _position_to_offset(self.original_line_starts, position.line, position.character)
        transpiled_offset = self._original_offset_to_transpiled_offset(original_offset)
        if transpiled_offset is None:
            return None
        return _offset_to_position(self.transpiled_line_starts, transpiled_offset)

    def transpiled_to_original_position(self, position: types.Position) -> types.Position | None:
        transpiled_offset = _position_to_offset(self.transpiled_line_starts, position.line, position.character)
        original_offset = self._transpiled_offset_to_original_offset(transpiled_offset)
        if original_offset is None:
            return None
        return _offset_to_position(self.original_line_starts, original_offset)

    def transpiled_to_original_range(self, range_: types.Range) -> types.Range | None:
        start = self.transpiled_to_original_position(range_.start)
        end = self.transpiled_to_original_position(range_.end)
        if start is None or end is None:
            return None
        return types.Range(start=start, end=end)
