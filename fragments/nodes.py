from dataclasses import dataclass
from typing import Protocol

from fragments.template import Python


class ASTNode(Protocol):
    def python(self, indent: int) -> Python: ...


@dataclass
class ASTFragment:
    children: list[ASTNode]

    def python(self, indent: int) -> Python:
        python = Python(indent)
        python.add('result = ""')
        for child in self.children:
            python.include(child.python(indent))
        python.add("return result")
        return python


@dataclass
class ASTHTMLElement:
    name: str
    attributes: list["ASTHTMLAttribute"]
    children: list[ASTNode]
    one_line: bool

    def python(self, indent: int) -> Python:
        python = Python(indent)
        python.add(f'result += "<{self.name}"')

        for attribute in self.attributes:
            python.add('result += " "')
            python.include(attribute.python(indent))

        python.add('result += ">"')

        for child in self.children:
            python.include(child.python(indent))

        python.add(f'result += "</{self.name}>"')
        return python


@dataclass
class ASTHTMLAttribute:
    name: str
    value: str | None
    interpolation: "ASTInterpolation | None"

    def python(self, indent: int) -> Python:
        result = Python(indent)
        result.add(f'result += "{self.name}"')

        if self.value is not None:
            result.add(f'result += "=\\"{self.value}\\""')
        elif self.interpolation is not None:
            result.add(f'result += "=\\"{self.interpolation.expression}\\""')
            result.include(self.interpolation.python(indent))

        return result


@dataclass
class ASTHTMLText:
    text: str

    def python(self, indent: int) -> Python:
        result = Python(indent)
        result.add(f'result += "{self.text}"')
        return result


@dataclass
class ASTForBlock:
    iterator: str
    iterable: str
    children: list[ASTNode]

    def python(self, indent: int) -> Python:
        result = Python(indent)
        result.add("for " + self.iterator + " in " + self.iterable + ":")
        for child in self.children:
            result.include(child.python(indent + 1))
        return result


@dataclass
class ASTIfBlock:
    condition: str
    children: list[ASTNode]

    def python(self, indent: int) -> Python:
        result = Python(indent)
        result.add("if " + self.condition + ":")
        for child in self.children:
            result.include(child.python(indent + 1))
        return result


@dataclass
class ASTWhileBlock:
    condition: str
    children: list[ASTNode]

    def python(self, indent: int) -> Python:
        result = Python(indent)
        result.add("while " + self.condition + ":")
        for child in self.children:
            result.include(child.python(indent + 1))
        return result


@dataclass
class ASTInterpolation:
    expression: str

    def python(self, indent: int) -> Python:
        result = Python(indent)
        result.add(f"result += {self.expression}")
        return result
