from dataclasses import dataclass, field
from typing import Sequence

from fragments.transpiled_code_writer import TranspiledCodeWriter

type ASTHTMLChild = ASTHTMLElement | ASTHTMLComment | ASTHTMLText | ASTInterpolation | ASTComponent | ASTScript | ASTStyle | ASTControlNode[ASTHTMLElement] | ASTControlNode[ASTComponent] | ASTControlNode[ASTTemplate] | ASTControlNode[ASTScript] | ASTControlNode[ASTStyle] | ASTDoctype | ASTChildrenSlot | ASTTemplate

IMPORT_PREFIX = "from fragments.html.elements import attribute_to_string, comment\n"
IMPORT_PREFIX_LEN = len(IMPORT_PREFIX)


def transpile_children(children: Sequence["ASTHTMLChild"], writer: TranspiledCodeWriter) -> None:
    """Concatenate children onto a preceding string expression, converting interpolated values to strings."""
    for child in children:
        writer.write("+")
        if isinstance(child, ASTInterpolation):
            writer.write("str(")
            child.transpile(writer)
            writer.write(")")
        else:
            child.transpile(writer)


@dataclass(slots=True)
class ASTModule:
    source_start: int = field(compare=False)
    source_end: int = field(compare=False)

    children: list["ASTPython | ASTFragment"]

    def transpile(self, writer: TranspiledCodeWriter) -> None:
        writer.write(IMPORT_PREFIX)
        for child in self.children:
            child.transpile(writer)


@dataclass(slots=True)
class ASTPython:
    """Vanilla Python code, copied into the transpiled code unchanged."""

    source_start: int = field(compare=False)
    source_end: int = field(compare=False)
    content: str

    def transpile(self, writer: TranspiledCodeWriter) -> None:
        writer.map(self.source_start, self.source_end)


@dataclass(slots=True)
class ASTFragment:
    source_start: int = field(compare=False)
    source_end: int = field(compare=False)

    children: list["ASTHTMLChild"]

    def transpile(self, writer: TranspiledCodeWriter) -> None:
        writer.write('""')
        transpile_children(self.children, writer)


@dataclass(slots=True)
class ASTHTMLElement:
    source_start: int = field(compare=False)
    source_end: int = field(compare=False)

    name: str
    attributes: dict[str, "ASTHTMLAttribute"]
    children: Sequence["ASTHTMLChild"]
    one_line: bool

    def transpile(self, writer: TranspiledCodeWriter) -> None:
        writer.write(f'f"<{self.name}')
        for attribute in self.attributes.values():
            writer.write(" ")
            attribute.transpile(writer)

        if self.one_line:
            writer.write(' />"')
            return

        writer.write('>"')
        transpile_children(self.children, writer)
        writer.write(f'+"</{self.name}>"')


@dataclass(slots=True)
class ASTControlNode[T: (ASTHTMLElement, ASTComponent, ASTTemplate, ASTScript, ASTStyle)]:
    source_start: int = field(compare=False)
    source_end: int = field(compare=False)

    if_interpolation: "ASTInterpolation | None"
    for_interpolation: "ASTInterpolation | None"
    child: T

    def transpile(self, writer: TranspiledCodeWriter) -> None:
        """Emit a generator expression for `for` (filtered per item by `if`, if present), or a ternary for a lone `if`.

        The `if` condition is parenthesised because both a comprehension `if` clause and a ternary condition only accept a
        disjunction, so an unparenthesised nested ternary, lambda or walrus would otherwise be a syntax error.
        """
        if self.for_interpolation is not None:
            writer.write("''.join(str(")
            self.child.transpile(writer)
            writer.write(") for ")
            self.for_interpolation.transpile(writer)
            if self.if_interpolation is not None:
                writer.write(" if (")
                self.if_interpolation.transpile(writer)
                writer.write(")")
            writer.write(")")
            return

        if self.if_interpolation is None:
            return

        writer.write("(")
        self.child.transpile(writer)
        writer.write(" if (")
        self.if_interpolation.transpile(writer)
        writer.write(") else '')")

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
class ASTTemplate:
    """The `<Template>` meta element: renders its children with no wrapping element, so it can carry `if` and `for`."""

    source_start: int = field(compare=False)
    source_end: int = field(compare=False)

    children: Sequence["ASTHTMLChild"]

    def transpile(self, writer: TranspiledCodeWriter) -> None:
        writer.write('""')
        transpile_children(self.children, writer)


@dataclass(slots=True)
class ASTComponent:
    source_start: int = field(compare=False)
    source_end: int = field(compare=False)

    name: "ASTComponentName"
    arguments: dict[str, "ASTComponentArgument"]
    children: Sequence["ASTHTMLChild"]
    self_closing: bool

    def transpile(self, writer: TranspiledCodeWriter) -> None:
        self.name.transpile(writer)
        writer.write("(")

        if not self.self_closing:
            writer.write('children=""')
            transpile_children(self.children, writer)
            writer.write(",")

        for argument in self.arguments.values():
            argument.transpile(writer)
            writer.write(",")

        writer.write(")")


@dataclass(slots=True)
class ASTComponentName:
    source_start: int = field(compare=False)
    source_end: int = field(compare=False)

    name: str

    def transpile(self, writer: TranspiledCodeWriter) -> None:
        writer.map(self.source_start, self.source_end)


@dataclass(slots=True)
class ASTComponentArgument:
    source_start: int = field(compare=False)
    source_end: int = field(compare=False)

    name: str
    string_literal: str | None
    interpolation: "ASTInterpolation | None"

    def transpile(self, writer: TranspiledCodeWriter) -> None:
        writer.map(self.source_start, self.source_start + len(self.name))
        writer.write("=")

        if self.string_literal is not None:
            writer.write(self.string_literal)
            return

        assert self.interpolation is not None
        self.interpolation.transpile(writer)


@dataclass(slots=True)
class ASTDoctype:
    source_start: int = field(compare=False)
    source_end: int = field(compare=False)

    def transpile(self, writer: TranspiledCodeWriter) -> None:
        writer.write('"<!DOCTYPE html>"')


@dataclass(slots=True)
class ASTHTMLComment:
    source_start: int = field(compare=False)
    source_end: int = field(compare=False)

    content: str

    def transpile(self, writer: TranspiledCodeWriter) -> None:
        writer.write(f"comment({self.content!r})")


@dataclass(slots=True)
class ASTHTMLAttribute:
    source_start: int = field(compare=False)
    source_end: int = field(compare=False)

    name: str
    string_literal: str | None
    interpolation: "ASTInterpolation | None"

    def transpile(self, writer: TranspiledCodeWriter) -> None:
        if self.string_literal is not None:
            escaped_literal = self.string_literal.replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r")
            writer.write(f"{{attribute_to_string('{self.name}',{escaped_literal})}}")
            return

        if self.interpolation is None:
            writer.write(self.name)
            return

        writer.write(f"{{attribute_to_string('{self.name}',")
        self.interpolation.transpile(writer)
        writer.write(")}")


@dataclass(slots=True)
class ASTHTMLText:
    source_start: int = field(compare=False)
    source_end: int = field(compare=False)

    text: str

    def transpile(self, writer: TranspiledCodeWriter) -> None:
        writer.write(repr(self.text))


@dataclass(slots=True)
class ASTScript:
    """A `<script>` element. `body` is `None` when the tag is self-closing."""

    source_start: int = field(compare=False)
    source_end: int = field(compare=False)

    attributes: dict[str, "ASTHTMLAttribute"]
    body: "ASTJSText | None"

    def transpile(self, writer: TranspiledCodeWriter) -> None:
        writer.write('f"<script')
        for attribute in self.attributes.values():
            writer.write(" ")
            attribute.transpile(writer)

        if self.body is None:
            writer.write(' />"')
            return

        writer.write('>"+')
        self.body.transpile(writer)
        writer.write('+"</script>"')


@dataclass(slots=True)
class ASTJSText:
    """The raw body of a `<script>` element, passed through verbatim."""

    source_start: int = field(compare=False)
    source_end: int = field(compare=False)

    text: str

    def transpile(self, writer: TranspiledCodeWriter) -> None:
        writer.write(repr(self.text))


@dataclass(slots=True)
class ASTStyle:
    """A `<style>` element. `body` is `None` when the tag is self-closing."""

    source_start: int = field(compare=False)
    source_end: int = field(compare=False)

    attributes: dict[str, "ASTHTMLAttribute"]
    body: "ASTCSSText | None"

    def transpile(self, writer: TranspiledCodeWriter) -> None:
        writer.write('f"<style')
        for attribute in self.attributes.values():
            writer.write(" ")
            attribute.transpile(writer)

        if self.body is None:
            writer.write(' />"')
            return

        writer.write('>"+')
        self.body.transpile(writer)
        writer.write('+"</style>"')


@dataclass(slots=True)
class ASTCSSText:
    """The raw body of a `<style>` element, passed through verbatim."""

    source_start: int = field(compare=False)
    source_end: int = field(compare=False)

    text: str

    def transpile(self, writer: TranspiledCodeWriter) -> None:
        writer.write(repr(self.text))


@dataclass(slots=True)
class ASTInterpolation:
    source_start: int = field(compare=False)
    source_end: int = field(compare=False)
    expression_start: int = field(compare=False)

    expression: str

    def transpile(self, writer: TranspiledCodeWriter) -> None:
        writer.map(self.expression_start, self.expression_start + len(self.expression))


@dataclass(slots=True)
class ASTChildrenSlot:
    source_start: int = field(compare=False)
    source_end: int = field(compare=False)

    def transpile(self, writer: TranspiledCodeWriter) -> None:
        writer.write("children")
