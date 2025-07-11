from dataclasses import dataclass
from typing import Protocol

from fragments.template import Template


class Node(Protocol):
    def template(self, indent: int) -> Template: ...


@dataclass
class Fragment:
    name: str
    parameters: str
    body: str
    children: list[Node]

    def template(self, indent: int) -> Template:
        outer = Template(indent)
        outer.add(f"frag {self.name}({self.parameters}):")
        inner = Template(indent + 1)
        inner.add(self.body)
        inner.add('result = ""')
        for child in self.children:
            inner.include(child.template(indent + 1))
        outer.include(inner)
        return outer


@dataclass
class HTMLElement:
    name: str
    attributes: list["HTMLAttribute"]
    children: list[Node]
    one_line: bool

    def template(self, indent: int) -> Template:
        result = Template(indent)
        result.add_string_to_result(f"<{self.name}")

        for attribute in self.attributes:
            result.add_string_to_result(" ")
            result.include(attribute.template(indent))

        result.add_string_to_result(">")

        for child in self.children:
            result.include(child.template(indent))

        result.add_string_to_result(f"</{self.name}>")
        return result


@dataclass
class HTMLAttribute:
    name: str
    value: str | None
    interpolation: "Interpolation | None"

    def template(self, indent: int) -> Template:
        result = Template(indent)
        result.add_string_to_result(self.name)

        if self.value is not None:
            result.add_string_to_result('=\\"')
            result.add_string_to_result(self.value)
            result.add_string_to_result('\\"')
        elif self.interpolation is not None:
            result.add_string_to_result('=\\"')
            result.include(self.interpolation.template(indent))

        return result


@dataclass
class HTMLText:
    text: str

    def template(self, indent: int) -> Template:
        result = Template(indent)
        result.add_string_to_result(self.text)
        return result


@dataclass
class ForBlock:
    iterator: str
    iterable: str
    children: list[Node]

    def template(self, indent: int) -> Template:
        result = Template(indent)
        result.add("for " + self.iterator + " in " + self.iterable + ":")
        for child in self.children:
            result.include(child.template(indent + 1))
        return result


@dataclass
class IfBlock:
    condition: str
    children: list[Node]

    def template(self, indent: int) -> Template:
        result = Template(indent)
        result.add("if " + self.condition + ":")
        for child in self.children:
            result.include(child.template(indent + 1))
        return result


@dataclass
class WhileBlock:
    condition: str
    children: list[Node]

    def template(self, indent: int) -> Template:
        result = Template(indent)
        result.add("while " + self.condition + ":")
        for child in self.children:
            result.include(child.template(indent + 1))
        return result


@dataclass
class Interpolation:
    expression: str

    def template(self, indent: int) -> Template:
        result = Template(indent)
        result.add_plain_to_result(self.expression)
        return result
