from fragments import grammar
from fragments.source import Source


def transpile(source_string: str) -> str:
    """Python code up to a fragment."""
    source: Source = Source.from_string(source_string)
    source, module = grammar.expect_module(source)
    module.transpile()
    return module.transpiled_content
