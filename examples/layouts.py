from typing import Any


def Base(children: str, title: str, header: str) -> str:
    return <>
        <html>
            <head>
                <title>{{ title }}</title>
            </head>
            <body>
                <h1>{{ header }}</h1>
                {{ sequence(children) }}
            </body>
        </html>
    </>
