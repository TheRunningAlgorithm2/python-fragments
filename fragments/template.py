from dataclasses import dataclass, field


@dataclass
class Python:
    """Represents the template that will be intserted in place of the fragment to the Python source."""

    indent: int
    lines: list["str | Python"] = field(default_factory=list)

    def add(self, text: str) -> None:
        """Add a single line to the template."""
        self.lines.append("    " * self.indent + text)

    def include(self, template: "Python"):
        self.lines.extend(template.lines)

    def __str__(self) -> str:
        return "\n".join(str(line) for line in self.lines)
