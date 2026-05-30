from fragments.types import Children


def Base(children: Children, title: str, header: str) -> str:
    return <>
        <html>
            <head>
                <title>{{ title }}</title>
            </head>
            <body>
                <h1>{{ header }}</h1>
                <Children... />
            </body>
        </html>
    </>
