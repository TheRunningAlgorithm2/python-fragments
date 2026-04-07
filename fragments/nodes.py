import json
from dataclasses import dataclass
from typing import Sequence


@dataclass
class ASTFragment:
    children: list["ASTHTMLElement | ASTHTMLText | ASTInterpolation"]

    __template__ = """sequence([{}])"""

    def python(self) -> str:
        return self.__template__.format(",".join(child.python() for child in self.children))


@dataclass
class ASTHTMLElement:
    name: str
    attributes: dict[str, "ASTHTMLAttribute"]
    children: Sequence["ASTHTMLElement | ASTHTMLText | ASTInterpolation"]
    one_line: bool

    __for_template__ = """sequence([{} for {}])"""
    __if_template__ = """{} if {} else ''"""
    __element_template__ = """el("{}", [{}], {}, {})"""

    def python(self) -> str:
        if_attribute = self.attributes.pop("if") if "if" in self.attributes else None
        for_attribute = self.attributes.pop("for") if "for" in self.attributes else None

        attributes = "{" + ",".join(attribute.python() for attribute in self.attributes.values()) + "}"
        result = self.__element_template__.format(self.name, ",".join(child.python() for child in self.children), attributes, self.one_line)

        if if_attribute is not None:
            assert if_attribute.interpolation is not None
            result = self.__if_template__.format(result, if_attribute.interpolation.python())

        if for_attribute is not None:
            assert for_attribute.interpolation is not None
            result = self.__for_template__.format(result, for_attribute.interpolation.python())

        return result


@dataclass
class ASTHTMLAttribute:
    name: str
    value: str | None
    interpolation: "ASTInterpolation | None"

    __value_template__ = '"{}": "{}"'
    __interpolation_template = '"{}": {}'

    def python(self) -> str:
        if self.value is not None:
            return self.__value_template__.format(self.name, self.value)

        assert self.interpolation is not None
        return self.__interpolation_template.format(self.name, self.interpolation.python())


@dataclass
class ASTHTMLText:
    text: str

    def python(self) -> str:
        return f'"{self.text}"'


@dataclass
class ASTInterpolation:
    expression: str

    def python(self) -> str:
        return self.expression
