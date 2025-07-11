from fragments import grammar
from fragments.nodes import ForBlock, HTMLAttribute, HTMLElement, HTMLText, IfBlock, Interpolation, WhileBlock


def test_empty():
    """The most basic type of fragment, one that contains nothing at all."""
    with open("tests/data/empty.pyf", "r") as f:
        source = f.read()

    source, fragment = grammar.expect_fragment(source)

    assert source == "\n"

    assert fragment.name == "Test"
    assert fragment.parameters == ""
    assert fragment.body == ""
    assert fragment.children == []


def test_element_only():
    """A fragment that has only one child which is a single HTML Element."""
    with open("tests/data/element-only.pyf", "r") as f:
        source = f.read()

    source, fragment = grammar.expect_fragment(source)

    assert source == "\n"

    assert fragment.name == "Test"
    assert fragment.parameters == ""
    assert fragment.body == ""
    assert fragment.children == [HTMLElement("h1", [], [], False)]


def test_element_text():
    """A fragment that only has one child which is a single HTML Element with some text inside."""
    with open("tests/data/element-text.pyf", "r") as f:
        source = f.read()

    source, fragment = grammar.expect_fragment(source)

    assert source == "\n"

    assert fragment.name == "Test"
    assert fragment.parameters == ""
    assert fragment.body == ""
    assert fragment.children == [HTMLElement("h1", [], [HTMLText("Hello")], False)]


def test_element_attributes():
    """A fragment that only has one child which is a single HTML Element with some text inside."""
    with open("tests/data/element-attributes.pyf", "r") as f:
        source = f.read()

    source, fragment = grammar.expect_fragment(source)

    assert source == "\n"

    assert fragment.name == "Test"
    assert fragment.parameters == ""
    assert fragment.body == ""
    assert fragment.children == [HTMLElement("div", [HTMLAttribute("hx-get", "/api/resource", None)], [], False)]


def test_element_children():
    """A fragment that only has one child which which also has a child."""
    with open("tests/data/element-children.pyf", "r") as f:
        source = f.read()

    source, fragment = grammar.expect_fragment(source)

    assert source == "\n"

    assert fragment.name == "Test"
    assert fragment.parameters == ""
    assert fragment.body == ""
    assert fragment.children == [HTMLElement("div", [], [HTMLElement("h1", [], [HTMLText("Hello")], False)], False)]


def test_whitespace():
    """A fragment with several children that makes use of whitespace."""
    with open("tests/data/whitespace.pyf", "r") as f:
        source = f.read()

    source, fragment = grammar.expect_fragment(source)

    assert source == "\n"

    assert fragment.name == "WhiteSpaceTest"
    assert fragment.parameters == ""
    assert fragment.body == ""
    assert fragment.children == [HTMLElement("h1", [], [HTMLText("Hello")], False), HTMLElement("p", [], [HTMLText("World")], False)]


def test_interpolation():
    """A fragment with an interpolation expression in."""
    with open("tests/data/interpolation.pyf", "r") as f:
        source = f.read()

    source, fragment = grammar.expect_fragment(source)

    assert source == "\n"

    assert fragment.name == "InterpolationTest"
    assert fragment.parameters == ""
    assert fragment.body == ""
    assert fragment.children == [Interpolation("value")]


def test_attribute_interpolation():
    """A fragment with an HTML Element with an interpolated attribute."""
    with open("tests/data/attribute-interpolation.pyf", "r") as f:
        source = f.read()

    source, fragment = grammar.expect_fragment(source)

    assert source == "\n"

    assert fragment.name == "AttributeInterpolationTest"
    assert fragment.parameters == ""
    assert fragment.body == ""
    assert fragment.children == [HTMLElement("div", [HTMLAttribute("data", None, Interpolation("data"))], [], False)]


def test_for_block():
    with open("tests/data/for-block.pyf", "r") as f:
        source = f.read()

    source, fragment = grammar.expect_fragment(source)

    assert source == "\n"

    assert fragment.name == "ForBlockTest"
    assert fragment.parameters == ""
    assert fragment.body == ""
    assert fragment.children == [ForBlock("item", "items", [HTMLElement("div", [], [], False)])]


def test_if_block():
    with open("tests/data/if-block.pyf", "r") as f:
        source = f.read()

    source, fragment = grammar.expect_fragment(source)

    assert source == "\n"

    assert fragment.name == "IfBlockTest"
    assert fragment.parameters == ""
    assert fragment.body == ""
    assert fragment.children == [IfBlock("value is not None", [HTMLElement("div", [], [], False)])]


def test_while_block():
    with open("tests/data/while-block.pyf", "r") as f:
        source = f.read()

    source, fragment = grammar.expect_fragment(source)

    assert source == "\n"

    assert fragment.name == "WhileBlockTest"
    assert fragment.parameters == ""
    assert fragment.body == ""
    assert fragment.children == [WhileBlock("value is not None", [HTMLElement("div", [], [], False)])]


def test_exercise_list():
    with open("tests/data/exercise-list.pyf", "r") as f:
        source = f.read()

    source, fragment = grammar.expect_fragment(source)

    assert source == "\n"

    assert fragment.name == "ExerciseList"
    assert fragment.parameters == ""
    assert fragment.body == ""
    assert fragment.children == [
        HTMLElement(
            "ul",
            [],
            [
                ForBlock(
                    "exercise",
                    "exercises",
                    [
                        HTMLElement(
                            "li",
                            [HTMLAttribute("id", None, Interpolation("exercise.id"))],
                            [Interpolation("exercise.name")],
                            False,
                        )
                    ],
                )
            ],
            False,
        )
    ]


def test_parameters():
    with open("tests/data/parameters.pyf", "r") as f:
        source = f.read()

    source, fragment = grammar.expect_fragment(source)

    assert source == "\n"

    assert fragment.name == "ParameterTest"
    assert fragment.parameters == "a: int, b: int"
    assert fragment.body == ""
    assert fragment.children == [Interpolation("a + b")]


def test_body():
    with open("tests/data/body.pyf", "r") as f:
        source = f.read()

    source, fragment = grammar.expect_fragment(source)

    assert source == "\n"

    assert fragment.name == "BodyTest"
    assert fragment.parameters == ""
    assert fragment.body == 'title = "hello, world"\n    subtitle = "this is a test"\n    '
    assert fragment.children == [
        HTMLElement("h1", [], [Interpolation("title")], False),
        HTMLElement("h2", [], [Interpolation("subtitle")], False),
    ]
