from fragments import grammar
from fragments.source import Source
from fragments.transpiled_code_writer import TranspiledCodeWriter


def transpile(source_string: str) -> str:
    """Python code up to a fragment."""
    source: Source = Source.from_string(source_string)
    source, module = grammar.expect_module(source)
    writer = TranspiledCodeWriter(source_string)
    module.transpile(writer)
    return writer.transpiled_content()
