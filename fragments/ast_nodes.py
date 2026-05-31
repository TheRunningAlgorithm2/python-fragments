from dataclasses import dataclass, field
from typing import Sequence

type ASTHTMLChild = ASTHTMLElement | ASTHTMLComment | ASTHTMLText | ASTInterpolation | ASTComponent | ASTControlNode | ASTDoctype | ASTChildrenSlot

IMPORT_PREFIX = "from fragments.html.elements import attribute_to_string, comment\n"
IMPORT_PREFIX_LEN = len(IMPORT_PREFIX)


@dataclass(slots=True)
class ASTModule:
    source_start: int = field(compare=False)
    source_end: int = field(compare=False)

    children: list["ASTPython | ASTFragment"]

    transpiled_content: str = field(init=False)
    transpiled_start: int = field(init=False)
    transpiled_end: int = field(init=False)

    __template__: str = "{}\n{}"

    def transpile(self, transpiled_start: int = 0) -> None:
        """Build transpiled outputs for the module."""
        self.transpiled_start = transpiled_start
        self.transpiled_content = IMPORT_PREFIX

        for child in self.children:
            child.transpile(self.transpiled_start + len(self.transpiled_content))
            self.transpiled_content += child.transpiled_content

        self.transpiled_end = self.transpiled_start + len(self.transpiled_content)

    def map_offset(self, offset: int) -> int | None:
        for owner in self.children:
            if owner.source_start <= offset <= owner.source_end:
                return owner.map_offset(offset)

    def unmap_offset(self, offset: int) -> int | None:
        for owner in self.children:
            if owner.transpiled_start <= offset <= owner.transpiled_end:
                return owner.unmap_offset(offset)


@dataclass(slots=True)
class ASTPython:
    """Build transpiled outputs for the vanilla Python code."""

    source_start: int = field(compare=False)
    source_end: int = field(compare=False)
    content: str

    transpiled_content: str = field(init=False)
    transpiled_start: int = field(init=False)
    transpiled_end: int = field(init=False)

    def transpile(self, transpiled_start: int) -> None:
        self.transpiled_start = transpiled_start
        self.transpiled_content = self.content
        self.transpiled_end = self.transpiled_start + len(self.transpiled_content)

    def map_offset(self, offset: int) -> int | None:
        if self.source_start <= offset <= self.source_end:
            specific_offset = offset - self.source_start
            return self.transpiled_start + specific_offset

        return None

    def unmap_offset(self, offset: int) -> int | None:
        if self.transpiled_start <= offset <= self.transpiled_end:
            specific_offset = offset - self.transpiled_start
            return self.source_start + specific_offset

        return None


@dataclass(slots=True)
class ASTFragment:
    source_start: int = field(compare=False)
    source_end: int = field(compare=False)

    children: list["ASTHTMLChild"]

    transpiled_content: str = field(init=False)
    transpiled_start: int = field(init=False)
    transpiled_end: int = field(init=False)

    def transpile(self, transpiled_start: int) -> None:
        self.transpiled_start = transpiled_start
        self.transpiled_content = '""'

        for child in self.children:
            self.transpiled_content += "+"
            if isinstance(child, ASTInterpolation):
                self.transpiled_content += "str("
            child.transpile(self.transpiled_start + len(self.transpiled_content))
            self.transpiled_content += child.transpiled_content
            if isinstance(child, ASTInterpolation):
                self.transpiled_content += ")"
        self.transpiled_end = self.transpiled_start + len(self.transpiled_content)

    def map_offset(self, offset: int) -> int | None:
        for owner in self.children:
            if owner.source_start <= offset <= owner.source_end:
                return owner.map_offset(offset)

        return None

    def unmap_offset(self, offset: int) -> int | None:
        for owner in self.children:
            if owner.transpiled_start <= offset <= owner.transpiled_end:
                return owner.unmap_offset(offset)

        return None


@dataclass(slots=True)
class ASTHTMLElement:
    source_start: int = field(compare=False)
    source_end: int = field(compare=False)

    name: str
    attributes: dict[str, "ASTHTMLAttribute"]
    children: Sequence["ASTHTMLChild"]
    one_line: bool

    transpiled_content: str = field(init=False)
    transpiled_start: int = field(init=False)
    transpiled_end: int = field(init=False)

    def transpile(self, transpiled_start: int) -> None:
        self.transpiled_start = transpiled_start
        self.transpiled_content = f'f"<{self.name}'

        for attribute in self.attributes.values():
            self.transpiled_content += " "
            attribute.transpile(self.transpiled_start + len(self.transpiled_content))
            self.transpiled_content += attribute.transpiled_content

        if self.one_line:
            self.transpiled_content += ' />"'
            self.transpiled_end = self.transpiled_start + len(self.transpiled_content)
            return

        self.transpiled_content += '>"'

        for child in self.children:
            self.transpiled_content += "+"
            if isinstance(child, ASTInterpolation):
                self.transpiled_content += "str("
            child.transpile(self.transpiled_start + len(self.transpiled_content))
            self.transpiled_content += child.transpiled_content
            if isinstance(child, ASTInterpolation):
                self.transpiled_content += ")"

        self.transpiled_content += f'+"</{self.name}>"'
        self.transpiled_end = self.transpiled_start + len(self.transpiled_content)

    def map_offset(self, offset: int) -> int | None:
        for attribute in self.attributes.values():
            if attribute.source_start <= offset <= attribute.source_end:
                return attribute.map_offset(offset)

        for child in self.children:
            if child.source_start <= offset <= child.source_end:
                return child.map_offset(offset)

        return None

    def unmap_offset(self, offset: int) -> int | None:
        for attribute in self.attributes.values():
            if attribute.transpiled_start <= offset <= attribute.transpiled_end:
                return attribute.unmap_offset(offset)

        for child in self.children:
            if child.transpiled_start <= offset <= child.transpiled_end:
                return child.unmap_offset(offset)

        return None


@dataclass(slots=True)
class ASTControlNode[T: (ASTHTMLElement, ASTComponent)]:
    source_start: int = field(compare=False)
    source_end: int = field(compare=False)

    if_interpolation: "ASTInterpolation | None"
    for_interpolation: "ASTInterpolation | None"
    child: T

    transpiled_content: str = field(init=False)
    transpiled_start: int = field(init=False)
    transpiled_end: int = field(init=False)

    __for_template__: str = "''.join(str({}) for {})"
    __if_template__: str = "({} if {} else '')"

    def transpile(self, transpiled_start: int) -> None:
        self.transpiled_start = transpiled_start
        if self.for_interpolation is not None:
            self.child.transpile(transpiled_start + 12)  # ''.join(str(
            self.for_interpolation.transpile(self.child.transpiled_end + 6)  # child + ) for
            self.transpiled_content = self.__for_template__.format(self.child.transpiled_content, self.for_interpolation.transpiled_content)
        elif self.if_interpolation is not None:
            self.child.transpile(transpiled_start + 1)  # ( before child
            self.if_interpolation.transpile(self.child.transpiled_end + 4)  # " if "
            self.transpiled_content = self.__if_template__.format(self.child.transpiled_content, self.if_interpolation.transpiled_content)
        self.transpiled_end = self.transpiled_start + len(self.transpiled_content)

    def map_offset(self, offset: int) -> int | None:
        if self.if_interpolation is not None and self.if_interpolation.source_start <= offset <= self.if_interpolation.source_end:
            return self.if_interpolation.map_offset(offset)

        if self.for_interpolation is not None and self.for_interpolation.source_start <= offset <= self.for_interpolation.source_end:
            return self.for_interpolation.map_offset(offset)

        if self.child.source_start <= offset <= self.child.source_end:
            return self.child.map_offset(offset)

        return None

    def unmap_offset(self, offset: int) -> int | None:
        if self.child.transpiled_start <= offset <= self.child.transpiled_end:
            return self.child.unmap_offset(offset)

        if self.if_interpolation is not None and self.if_interpolation.transpiled_start <= offset <= self.if_interpolation.transpiled_end:
            return self.if_interpolation.unmap_offset(offset)

        if self.for_interpolation is not None and self.for_interpolation.transpiled_start <= offset <= self.for_interpolation.transpiled_end:
            return self.for_interpolation.unmap_offset(offset)

        return None

    @classmethod
    def wrap_child(
        cls,
        child: T,
        if_interpolation: "ASTInterpolation | None",
        for_interpolation: "ASTInterpolation | None",
    ) -> "ASTControlNode[T] | T":
        """If the child needs a control node, wrap it."""
        if if_interpolation is None and for_interpolation is None:
            return child

        return ASTControlNode(child.source_start, child.source_end, if_interpolation, for_interpolation, child)


@dataclass(slots=True)
class ASTComponent:
    source_start: int = field(compare=False)
    source_end: int = field(compare=False)

    name: "ASTComponentName"
    arguments: dict[str, "ASTComponentArgument"]
    children: Sequence["ASTHTMLChild"]

    transpiled_content: str = field(init=False)
    transpiled_start: int = field(init=False)
    transpiled_end: int = field(init=False)

    __template__: str = """{}({},{})"""

    def transpile(self, transpiled_start: int) -> None:
        self.transpiled_start = transpiled_start
        self.name.transpile(self.transpiled_start)
        self.transpiled_content = self.name.transpiled_content + '(""'

        for child in self.children:
            child.transpile(self.transpiled_start + len(self.transpiled_content))
            self.transpiled_content += "+" + child.transpiled_content

        self.transpiled_content += ","

        for argument in self.arguments.values():
            argument.transpile(self.transpiled_start + len(self.transpiled_content))
            self.transpiled_content += argument.transpiled_content + ","

        self.transpiled_content += ")"
        self.transpiled_end = self.transpiled_start + len(self.transpiled_content)

    def map_offset(self, offset: int) -> int | None:
        if self.name.source_start < offset < self.name.source_end:
            return self.name.map_offset(offset)

        for attribute in self.arguments.values():
            if attribute.source_start <= offset <= attribute.source_end:
                return attribute.map_offset(offset)

        for child in self.children:
            if child.source_start <= offset <= child.source_end:
                return child.map_offset(offset)

        return None

    def unmap_offset(self, offset: int) -> int | None:
        if self.name.transpiled_start < offset < self.name.transpiled_end:
            return self.name.unmap_offset(offset)

        for attribute in self.arguments.values():
            if attribute.transpiled_start <= offset <= attribute.transpiled_end:
                return attribute.unmap_offset(offset)

        for child in self.children:
            if child.transpiled_start <= offset <= child.transpiled_end:
                return child.unmap_offset(offset)

        return None


@dataclass(slots=True)
class ASTComponentName:
    source_start: int = field(compare=False)
    source_end: int = field(compare=False)

    name: str

    transpiled_content: str = field(init=False)
    transpiled_start: int = field(init=False)
    transpiled_end: int = field(init=False)

    def transpile(self, offset: int) -> None:
        self.transpiled_start = offset
        self.transpiled_content = self.name
        self.transpiled_end = offset + len(self.name)

    def map_offset(self, offset: int) -> int | None:
        if self.source_start <= offset <= self.source_end:
            specific_offset = offset - self.source_start
            return self.transpiled_start + specific_offset

        return None

    def unmap_offset(self, offset: int) -> int | None:
        if self.transpiled_start <= offset <= self.transpiled_end:
            specific_offset = offset - self.transpiled_start
            return self.source_start + specific_offset

        return None


@dataclass(slots=True)
class ASTComponentArgument:
    source_start: int = field(compare=False)
    source_end: int = field(compare=False)

    name: str
    string_literal: str | None
    interpolation: "ASTInterpolation | None"

    transpiled_content: str = field(init=False)
    transpiled_start: int = field(init=False)
    transpiled_end: int = field(init=False)

    __template__: str = "{}={}"

    def transpile(self, transpiled_start: int) -> None:
        self.transpiled_start = transpiled_start

        if self.string_literal is not None:
            self.transpiled_content = self.__template__.format(self.name, self.string_literal)
            self.transpiled_end = self.transpiled_start + len(self.transpiled_content)
            return

        assert self.interpolation is not None
        self.interpolation.transpile(self.transpiled_start + len(self.name) + 1)
        self.transpiled_content = self.__template__.format(self.name, self.interpolation.transpiled_content)
        self.transpiled_end = self.transpiled_start + len(self.transpiled_content)

    def map_offset(self, offset: int) -> int | None:
        if self.source_start <= offset <= self.source_start + len(self.name):
            specific_offset = offset - self.source_start
            return self.transpiled_start + specific_offset

        if self.interpolation is None:
            return None

        if self.interpolation.source_start <= offset <= self.interpolation.source_end:
            return self.interpolation.map_offset(offset)

        return None

    def unmap_offset(self, offset: int) -> int | None:
        if self.transpiled_start <= offset <= self.transpiled_start + len(self.name):
            specific_offset = offset - self.transpiled_start
            return self.source_start + specific_offset

        if self.interpolation is None:
            return None

        if self.interpolation.transpiled_start <= offset <= self.interpolation.transpiled_end:
            return self.interpolation.unmap_offset(offset)

        return None


@dataclass(slots=True)
class ASTDoctype:
    source_start: int = field(compare=False)
    source_end: int = field(compare=False)

    transpiled_content: str = field(init=False)
    transpiled_start: int = field(init=False)
    transpiled_end: int = field(init=False)

    def transpile(self, transpiled_start: int) -> None:
        self.transpiled_start = transpiled_start
        self.transpiled_content = '"<!DOCTYPE html>"'
        self.transpiled_end = self.transpiled_start + len(self.transpiled_content)

    def map_offset(self, offset: int) -> None:
        return None

    def unmap_offset(self, offset: int) -> None:
        return None


@dataclass(slots=True)
class ASTHTMLComment:
    source_start: int = field(compare=False)
    source_end: int = field(compare=False)

    content: str

    transpiled_content: str = field(init=False)
    transpiled_start: int = field(init=False)
    transpiled_end: int = field(init=False)

    __template__: str = """comment("{}")"""

    def transpile(self, transpiled_start: int) -> None:
        self.transpiled_start = transpiled_start
        escaped_content = self.content.replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r").replace('"', '\\"')
        self.transpiled_content = self.__template__.format(escaped_content)
        self.transpiled_end = self.transpiled_start + len(self.transpiled_content)

    def map_offset(self, offset: int) -> None:
        return None

    def unmap_offset(self, offset: int) -> None:
        return None


@dataclass(slots=True)
class ASTHTMLAttribute:
    source_start: int = field(compare=False)
    source_end: int = field(compare=False)

    name: str
    string_literal: str | None
    interpolation: "ASTInterpolation | None"

    transpiled_content: str = field(init=False)
    transpiled_start: int = field(init=False)
    transpiled_end: int = field(init=False)

    def transpile(self, transpiled_start: int) -> None:
        self.transpiled_start = transpiled_start
        self.transpiled_content = "{" + f"attribute_to_string('{self.name}',"

        if self.string_literal is not None:
            escaped_literal = self.string_literal.replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r")
            self.transpiled_content += escaped_literal + ")}"
            self.transpiled_end = self.transpiled_start + len(self.transpiled_content)
            return

        if self.interpolation is None:
            self.transpiled_content = f'"{self.name}"'
            self.transpiled_end = self.transpiled_start + len(self.transpiled_content)
            return

        self.interpolation.transpile(self.transpiled_start + len(self.transpiled_content))
        self.transpiled_content += self.interpolation.transpiled_content + ")}"
        self.transpiled_end = self.transpiled_start + len(self.transpiled_content)

    def map_offset(self, offset: int) -> int | None:
        if self.interpolation is None:
            return None

        if self.interpolation.source_start <= offset <= self.interpolation.source_end:
            return self.interpolation.map_offset(offset)

        return None

    def unmap_offset(self, offset: int) -> int | None:
        if self.interpolation is None:
            return None

        if self.interpolation.transpiled_start <= offset <= self.interpolation.transpiled_end:
            return self.interpolation.unmap_offset(offset)

        return None


@dataclass(slots=True)
class ASTHTMLText:
    source_start: int = field(compare=False)
    source_end: int = field(compare=False)

    text: str

    transpiled_content: str = field(init=False)
    transpiled_start: int = field(init=False)
    transpiled_end: int = field(init=False)

    __template__: str = '"{}"'

    def transpile(self, transpiled_start: int) -> None:
        self.transpiled_content = self.__template__.format(self.text.replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r").replace('"', '"'))
        self.transpiled_start = transpiled_start
        self.transpiled_end = self.transpiled_start + len(self.transpiled_content)

    def map_offset(self, offset: int) -> None:
        return None

    def unmap_offset(self, offset: int) -> None:
        return None


@dataclass(slots=True)
class ASTInterpolation:
    source_start: int = field(compare=False)
    source_end: int = field(compare=False)
    expression: str
    leading_whitespace: int
    trailing_whitespace: int

    transpiled_content: str = field(init=False)
    transpiled_start: int = field(init=False)
    transpiled_end: int = field(init=False)

    def transpile(self, transpiled_start: int) -> None:
        self.transpiled_content = self.expression.strip()
        self.transpiled_start = transpiled_start
        self.transpiled_end = self.transpiled_start + len(self.transpiled_content)

    def map_offset(self, offset: int) -> int | None:
        if self.source_start + 2 + self.leading_whitespace <= offset <= self.source_end - 2 - self.trailing_whitespace:
            specific_offset = offset - (self.source_start + self.leading_whitespace + 2)
            return self.transpiled_start + specific_offset

        return None

    def unmap_offset(self, offset: int) -> int | None:
        if self.transpiled_start <= offset <= self.transpiled_end:
            specific_offset = offset - self.transpiled_start
            return self.source_start + specific_offset + 2 + self.leading_whitespace

        return None


@dataclass(slots=True)
class ASTChildrenSlot:
    source_start: int = field(compare=False)
    source_end: int = field(compare=False)

    transpiled_content: str = field(init=False)
    transpiled_start: int = field(init=False)
    transpiled_end: int = field(init=False)

    def transpile(self, transpiled_start: int) -> None:
        self.transpiled_start = transpiled_start
        self.transpiled_content = "children"
        self.transpiled_end = transpiled_start + len("children")

    def map_offset(self, offset: int) -> None:
        return None

    def unmap_offset(self, offset: int) -> None:
        return None
