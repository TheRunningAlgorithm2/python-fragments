from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Source:
    content: str
    offset: int

    def remaining(self) -> str:
        return self.content[self.offset :]

    def eat(self, chars: int) -> "Source":
        return Source(self.content, self.offset + chars)

    def eat_whitespace(self) -> "tuple[Source, str]":
        new_content = self.remaining().lstrip()
        num_whitespace_chars = len(self.remaining()) - len(new_content)
        whitespace_chars = self.remaining()[:num_whitespace_chars]
        return self.eat(num_whitespace_chars), whitespace_chars

    def at_end(self) -> bool:
        return self.offset == len(self.content)

    @classmethod
    def from_string(cls, string: str) -> "Source":
        return Source(string, 0)
