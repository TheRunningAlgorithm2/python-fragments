from fragments import grammar
from fragments.nodes import ASTHTMLAttribute, ASTHTMLElement, ASTHTMLText, ASTInterpolation


def test_full():
    """A fragment that has only one child which is a single HTML Element."""
    with open("tests/data/full.py", "r") as f:
        source = f.read()
    source, fragment = grammar.expect_fragment(source)
    assert source == ""
    assert fragment.children == [
        ASTHTMLElement(
            "div",
            [ASTHTMLAttribute("classes", "flex flex-col gap-3", None)],
            [
                ASTHTMLElement(
                    "div",
                    [ASTHTMLAttribute("for", None, ASTInterpolation("item in user.items")), ASTHTMLAttribute("classes", "p-3 rounded-lg bg-gray-800", None)],
                    [
                        ASTHTMLElement("p", [ASTHTMLAttribute("style", None, ASTInterpolation('{"color": "red"}'))], [ASTInterpolation("item.name")], False),
                        ASTHTMLElement("p", [ASTHTMLAttribute("if", None, ASTInterpolation("item.description"))], [ASTInterpolation("item.description")], False),
                        ASTHTMLElement("p", [], [ASTHTMLText("This is an item")], False),
                        ASTHTMLElement("input", [], [], True),
                    ],
                    False,
                )
            ],
            False,
        )
    ]


# def test_element_only():
#     """A fragment that has only one child which is a single HTML Element."""
#     with open("tests/data/element-only.py", "r") as f:
#         source = f.read()

#     source, fragment = grammar.expect_fragment(source)

#     assert source == ""

#     assert fragment.children == [ASTHTMLElement("h1", [], [], False)]


# def test_element_text():
#     """A fragment that only has one child which is a single HTML Element with some text inside."""
#     with open("tests/data/element-text.pyf", "r") as f:
#         source = f.read()

#     source, fragment = grammar.expect_fragment(source)

#     assert source == "\n"

#     assert fragment.name == "Test"
#     assert fragment.parameters == ""
#     assert fragment.body == ""
#     assert fragment.children == [HTMLElement("h1", [], [HTMLText("Hello")], False)]


# def test_element_attributes():
#     """A fragment that only has one child which is a single HTML Element with some text inside."""
#     with open("tests/data/element-attributes.pyf", "r") as f:
#         source = f.read()

#     source, fragment = grammar.expect_fragment(source)

#     assert source == "\n"

#     assert fragment.name == "Test"
#     assert fragment.parameters == ""
#     assert fragment.body == ""
#     assert fragment.children == [HTMLElement("div", [HTMLAttribute("hx-get", "/api/resource", None)], [], False)]


# def test_element_children():
#     """A fragment that only has one child which which also has a child."""
#     with open("tests/data/element-children.pyf", "r") as f:
#         source = f.read()

#     source, fragment = grammar.expect_fragment(source)

#     assert source == "\n"

#     assert fragment.name == "Test"
#     assert fragment.parameters == ""
#     assert fragment.body == ""
#     assert fragment.children == [HTMLElement("div", [], [HTMLElement("h1", [], [HTMLText("Hello")], False)], False)]


# def test_whitespace():
#     """A fragment with several children that makes use of whitespace."""
#     with open("tests/data/whitespace.pyf", "r") as f:
#         source = f.read()

#     source, fragment = grammar.expect_fragment(source)

#     assert source == "\n"

#     assert fragment.name == "WhiteSpaceTest"
#     assert fragment.parameters == ""
#     assert fragment.body == ""
#     assert fragment.children == [HTMLElement("h1", [], [HTMLText("Hello")], False), HTMLElement("p", [], [HTMLText("World")], False)]


# def test_interpolation():
#     """A fragment with an interpolation expression in."""
#     with open("tests/data/interpolation.pyf", "r") as f:
#         source = f.read()

#     source, fragment = grammar.expect_fragment(source)

#     assert source == "\n"

#     assert fragment.name == "InterpolationTest"
#     assert fragment.parameters == ""
#     assert fragment.body == ""
#     assert fragment.children == [Interpolation("value")]


# def test_attribute_interpolation():
#     """A fragment with an HTML Element with an interpolated attribute."""
#     with open("tests/data/attribute-interpolation.pyf", "r") as f:
#         source = f.read()

#     source, fragment = grammar.expect_fragment(source)

#     assert source == "\n"

#     assert fragment.name == "AttributeInterpolationTest"
#     assert fragment.parameters == ""
#     assert fragment.body == ""
#     assert fragment.children == [HTMLElement("div", [HTMLAttribute("data", None, Interpolation("data"))], [], False)]


# def test_exercise_list():
#     with open("tests/data/exercise-list.pyf", "r") as f:
#         source = f.read()

#     source, fragment = grammar.expect_fragment(source)

#     assert source == "\n"

#     assert fragment.name == "ExerciseList"
#     assert fragment.parameters == ""
#     assert fragment.body == ""
#     assert fragment.children == [
#         HTMLElement(
#             "ul",
#             [],
#             [
#                 ForBlock(
#                     "exercise",
#                     "exercises",
#                     [
#                         HTMLElement(
#                             "li",
#                             [HTMLAttribute("id", None, Interpolation("exercise.id"))],
#                             [Interpolation("exercise.name")],
#                             False,
#                         )
#                     ],
#                 )
#             ],
#             False,
#         )
#     ]


# def test_parameters():
#     with open("tests/data/parameters.pyf", "r") as f:
#         source = f.read()

#     source, fragment = grammar.expect_fragment(source)

#     assert source == "\n"

#     assert fragment.name == "ParameterTest"
#     assert fragment.parameters == "a: int, b: int"
#     assert fragment.body == ""
#     assert fragment.children == [Interpolation("a + b")]


# def test_body():
#     with open("tests/data/body.pyf", "r") as f:
#         source = f.read()

#     source, fragment = grammar.expect_fragment(source)

#     assert source == "\n"

#     assert fragment.name == "BodyTest"
#     assert fragment.parameters == ""
#     assert fragment.body == 'title = "hello, world"\n    subtitle = "this is a test"\n    '
#     assert fragment.children == [
#         HTMLElement("h1", [], [Interpolation("title")], False),
#         HTMLElement("h2", [], [Interpolation("subtitle")], False),
#     ]
