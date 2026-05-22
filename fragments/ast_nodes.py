from dataclasses import dataclass, field
from typing import Sequence


@dataclass(slots=True)
class ASTModule:
    source_start: int = field(compare=False)
    source_end: int = field(compare=False)

    children: list["ASTPython | ASTFragment"]

    transpiled_content: str = field(init=False)
    transpiled_start: int = field(init=False)
    transpiled_end: int = field(init=False)

    __template__: str = "from fragments.html.elements import el, sequence, comment\n{}"

    def transpile(self, transpiled_start: int = 0) -> None:
        """Build transpiled outputs for the module."""
        self.transpiled_start = transpiled_start
        transpiled_start += len(self.__template__) - 2
        for child in self.children:
            child.transpile(transpiled_start)
            transpiled_start = child.transpiled_end

        children: str = "".join(child.transpiled_content for child in self.children)
        self.transpiled_content = self.__template__.format(children)
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

    children: list["ASTHTMLElement | ASTHTMLComment | ASTHTMLText | ASTInterpolation"]

    transpiled_content: str = field(init=False)
    transpiled_start: int = field(init=False)
    transpiled_end: int = field(init=False)

    __template__: str = """sequence([{}])"""

    def transpile(self, transpiled_start: int) -> None:
        self.transpiled_start = transpiled_start
        transpiled_start += 10
        for child in self.children:
            child.transpile(transpiled_start)
            transpiled_start = child.transpiled_end + 1
        transpiled_start -= 1

        self.transpiled_content = self.__template__.format(",".join(child.transpiled_content for child in self.children))
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
    if_attribute: "ASTInterpolation | None"
    for_attribute: "ASTInterpolation | None"
    children: Sequence["ASTHTMLElement | ASTHTMLComment | ASTHTMLText | ASTInterpolation"]
    one_line: bool

    transpiled_content: str = field(init=False)
    transpiled_start: int = field(init=False)
    transpiled_end: int = field(init=False)

    __for_template__: str = """sequence([{} for {}])"""
    __if_template__: str = """{} if {} else ''"""
    __element_template__: str = """el("{}",[{}],oneline={},{})"""
    __component_template__: str = """{}([{}],{})"""

    def transpile(self, transpiled_start: int) -> None:
        self.transpiled_start = transpiled_start

        if self.for_attribute is not None:
            transpiled_start += 10

        if self.name[0].capitalize() == self.name[0]:
            self._transpile_component_call(transpiled_start)
        else:
            self._transpile_element_call(transpiled_start)

        if self.if_attribute is not None:
            self.if_attribute.transpile(self.transpiled_end + 4)
            self.transpiled_content = self.__if_template__.format(self.transpiled_content, self.if_attribute.transpiled_content)
            self.transpiled_end = self.if_attribute.transpiled_end + 8
        elif self.for_attribute is not None:
            self.for_attribute.transpile(self.transpiled_end + 5)
            self.transpiled_content = self.__for_template__.format(self.transpiled_content, self.for_attribute.transpiled_content)
            self.transpiled_end = self.for_attribute.transpiled_end + 2

    def _transpile_element_call(self, start: int) -> None:
        transpiled_start = start + len(self.name) + 7
        for child in self.children:
            child.transpile(transpiled_start)
            transpiled_start = child.transpiled_end + 1
        transpiled_start -= 1
        children = ",".join(child.transpiled_content for child in self.children)

        oneline_offset = len(str(self.one_line))

        transpiled_start += 10 + oneline_offset + 1

        for attribute in self.attributes.values():
            attribute.transpile(transpiled_start)
            transpiled_start = attribute.transpiled_end + 1
        transpiled_start -= 1

        attributes = ",".join(attribute.transpiled_content for attribute in self.attributes.values())
        self.transpiled_content = self.__element_template__.format(self.name, children, self.one_line, attributes)
        self.transpiled_end = start + len(self.transpiled_content)

    def _transpile_component_call(self, start: int) -> None:
        transpiled_start = start + len(self.name) + 2
        for child in self.children:
            child.transpile(transpiled_start)
            transpiled_start = child.transpiled_end + 1
        transpiled_start -= 1
        children = ",".join(child.transpiled_content for child in self.children)

        if len(self.attributes) == 0:
            self.transpiled_content = self.__component_template__.format(self.name, children, "")
            self.transpiled_end = start + len(self.transpiled_content)
            return

        transpiled_start += 2
        for attribute in self.attributes.values():
            attribute.transpile(transpiled_start)
            transpiled_start = attribute.transpiled_end + 1

        attributes = ",".join(attribute.transpiled_content for attribute in self.attributes.values())
        self.transpiled_content = self.__component_template__.format(self.name, children, attributes)
        self.transpiled_end = start + len(self.transpiled_content)

    def map_offset(self, offset: int) -> int | None:
        for attribute in self.attributes.values():
            if attribute.source_start <= offset <= attribute.source_end:
                return attribute.map_offset(offset)

        for child in self.children:
            if child.source_start <= offset <= child.source_end:
                return child.map_offset(offset)

        if self.if_attribute is not None and self.if_attribute.source_start <= offset <= self.if_attribute.source_end:
            return self.if_attribute.map_offset(offset)

        if self.for_attribute is not None and self.for_attribute.source_start <= offset <= self.for_attribute.source_end:
            return self.for_attribute.map_offset(offset)

        return None

    def unmap_offset(self, offset: int) -> int | None:
        for attribute in self.attributes.values():
            if attribute.transpiled_start <= offset <= attribute.transpiled_end:
                return attribute.unmap_offset(offset)

        for child in self.children:
            if child.transpiled_start <= offset <= child.transpiled_end:
                return child.unmap_offset(offset)

        if self.if_attribute is not None and self.if_attribute.transpiled_start <= offset <= self.if_attribute.transpiled_end:
            return self.if_attribute.unmap_offset(offset)

        if self.for_attribute is not None and self.for_attribute.transpiled_start <= offset <= self.for_attribute.transpiled_end:
            return self.for_attribute.unmap_offset(offset)

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
        self.transpiled_content = self.__template__.format(self.content)
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
    value: str | None
    interpolation: "ASTInterpolation | None"

    transpiled_content: str = field(init=False)
    transpiled_start: int = field(init=False)
    transpiled_end: int = field(init=False)

    __value_template__: str = '{}="{}"'
    __interpolation_template__: str = "{}={}"

    def transpile(self, transpiled_start: int) -> None:
        self.transpiled_start = transpiled_start

        if self.value is not None:
            self.transpiled_content = self.__value_template__.format(self.name, self.value)
            self.transpiled_end = self.transpiled_start + len(self.transpiled_content)
            return

        assert self.interpolation is not None
        self.interpolation.transpile(self.transpiled_start + len(self.name) + 1)
        self.transpiled_content = self.__interpolation_template__.format(self.name, self.interpolation.transpiled_content)
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
        self.transpiled_content = self.__template__.format(self.text)
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
            specific_offset = offset - self.source_start - 2 - self.leading_whitespace
            return self.transpiled_start + specific_offset

        return None

    def unmap_offset(self, offset: int) -> int | None:
        if self.transpiled_start <= offset <= self.transpiled_end:
            specific_offset = offset - self.transpiled_start
            return self.source_start + specific_offset + 2 + self.leading_whitespace

        return None
