from fragments import grammar


def transpile(source: str) -> str:
    """Python code up to a fragment."""
    source, python = grammar.optional_regex(source, grammar.PYTHON)
    result = ""

    if python is not None:
        result = python

    while len(source) > 0:
        if source.lstrip().startswith("return <>"):
            spaces = len(source) - len(source.lstrip())
            indent = spaces // 4
            source = source.lstrip()
            source, fragment = grammar.expect_fragment(source)
            result += str(fragment.python(indent))
        else:
            source, python = grammar.expect_regex(source, grammar.PYTHON, "python source")
            result += python

    return result
