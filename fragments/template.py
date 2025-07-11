from dataclasses import dataclass, field


@dataclass
class Template:
    """Represents the template that will be intserted in place of the fragment to the Python source."""

    indent: int
    lines: list[str] = field(default_factory=list)

    def add(self, text: str) -> None:
        """Add a single line to the template."""
        self.lines.append("    " * self.indent + text)

    def add_plain_to_result(self, text: str) -> None:
        """Add a line to the template like:

        result += {text}"""
        self.lines.append("    " * self.indent + "result += " + text)

    def add_string_to_result(self, text: str) -> None:
        """Add a line to the template like:

        result += "{text}" """
        self.lines.append("    " * self.indent + 'result += "' + text + '"')

    def include(self, template: "Template"):
        self.lines.extend(template.lines)

    def __str__(self) -> str:
        return "\n".join(self.lines)
