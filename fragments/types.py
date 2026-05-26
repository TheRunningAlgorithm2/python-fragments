from typing import Protocol


class Stringable(Protocol):
    def __str__(self) -> str: ...


type Child = str | Stringable
type Children = list[Child]
