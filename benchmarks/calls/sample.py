from dataclasses import dataclass

import jinja2


@dataclass
class Post:
    title: str
    author: str
    summary: str

POSTS: list[Post] = [
    Post(title="Post 1", author="The Running Algorithm", summary="First post"),
    Post(title="Post 2", author="The Running Algorithm", summary="Second post"),
    Post(title="Post 3", author="The Running Algorithm", summary="Third post"),
]


def Articles() -> str:
    return <>
        <article for={{ post in POSTS }}>
            <h1>{{ post.title }}</h1>
            <p classes="byline">By {{ post.author }}</p>
            <p classes="summary">{{ post.summary }}</p>
        </article>
    </>


_jinja_environment = jinja2.Environment()
_jinja_template = _jinja_environment.from_string(
    "{% for post in posts %}"
    '<article><h1>{{ post.title }}</h1>'
    '<p classes="byline">By {{ post.author }}</p>'
    '<p classes="summary">{{ post.summary }}</p>'
    "</article>"
    "{% endfor %}"
)


def ArticlesJinja() -> str:
    return _jinja_template.render(posts=POSTS)


def ArticlesStringOnly() -> str:
    result = ""
    __template__ = """<article><h1>{}</h1><p classes="byline">By {}</p><p classes="summary">{}</p></article>"""

    for post in POSTS:
        result += __template__.format(post.title, post.author, post.summary)

    return result
