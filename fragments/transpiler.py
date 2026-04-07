from fragments import grammar


def transpile(source: str) -> str:
    """Python code up to a fragment."""
    source, python = grammar.optional_regex(source, grammar.PYTHON)
    result = ""

    if python is not None:
        result = python

    result = "from fragments.html.elements import el, sequence\n" + result

    while len(source) > 0:
        if source.lstrip().startswith("<>"):
            source_before = source
            source = source.lstrip()
            whitespace = source_before[: len(source_before) - len(source)]
            source, fragment = grammar.expect_fragment(source)
            result += whitespace + fragment.python()
        else:
            source, python = grammar.expect_regex(source, grammar.PYTHON, "python source")
            result += python

    return result
