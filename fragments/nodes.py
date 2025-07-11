from dataclasses import dataclass
from typing import Protocol


class Node(Protocol): ...


@dataclass
class Fragment:
    name: str
    parameters: str
    body: str
    children: list[Node]


@dataclass
class HTMLElement:
    name: str
    attributes: list["HTMLAttribute"]
    children: list[Node]
    one_line: bool


@dataclass
class HTMLAttribute:
    name: str
    value: str | None
    interpolation: "Interpolation | None"


@dataclass
class HTMLText:
    text: str


@dataclass
class ForBlock:
    iterator: str
    iterable: str
    children: list[Node]


@dataclass
class IfBlock:
    condition: str
    children: list[Node]


@dataclass
class WhileBlock:
    condition: str
    children: list[Node]


@dataclass
class Interpolation:
    expression: str
