# Black

Format the Python in your fragment files with [Black](https://black.readthedocs.io/). Everything inside `<>...</>` is left exactly as written.

## Installation

``` bash
pip install python-fragments[black]
```

This installs a supported version of Black alongside Fragments.

## How it works

Black can't parse fragment syntax, so Fragments does three things:

1. Swaps each fragment for a placeholder name.
2. Formats the resulting plain Python with Black.
3. Puts the original fragments back.

Black's internal parser reads your configuration and command line options, so supported featuresbehave exactly as expected.

## Features

### Supported

- Formatting all the Python outside fragments, including expressions that contain inline fragments.
- `[tool.black]` in `pyproject.toml`.
- Black's [command line options](#options) that control the code style, such as line length, string normalization, preview and target versions.
- Black's file discovery: directories, `.gitignore`, `include`, `exclude`, `extend-exclude` and `force-exclude`.
- `--check`, `--diff` and `--quiet`.
- Format document and format on save in editors, through the [language server](../../getting-started/lsp.md).
- A [pre-commit](#pre-commit) hook.

### Not supported

- Formatting inside fragments. Tags, attributes and the Python inside `{{ }}` interpolations are not changed.
- Notebooks and stubs. `.ipynb` and `.pyi` files are skipped when searching directories, and `--ipynb` and `--pyi` are rejected.
- Partial formatting. `--line-ranges` is rejected, and editors can't format only a selection.
- Standard input. `--code`, `--stdin-filename` and `-` are not supported.
- Black's cache and parallel workers. `--cache-dir`, `--no-cache` and `--workers` are accepted but have no effect.
- Files that don't parse. On the command line they're reported as `path:line:column: message` and the remaining files are still formatted. In editors they're left unchanged.

## Command line

``` bash
fragments black src/ app.py      # format files or directories in place
fragments black --check src/     # exit 1 if any file would change
fragments black --diff app.py    # print a diff instead of writing
fragments black -l 100 -S src/   # any Black option, on top of [tool.black]
```

| Exit code | Meaning                                                                                                    |
| --------- | ---------------------------------------------------------------------------------------------------------- |
| 0         | Success                                                                                                    |
| 1         | A file failed to parse, or `--check` found a file that would change                                        |
| 2         | No files given, a path doesn't exist, an option is invalid or unsupported, or the configuration is invalid |

### Options

`fragments black` accepts the following [command line options](https://black.readthedocs.io/en/stable/usage_and_configuration/the_basics.html#command-line-options):

| Support | Options                                                                                                                                                                                                   |
| ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Full    | `-l`, `-t`, `-S`, `-C`, `--preview`, `--unstable`, `--enable-unstable-feature`, `--include`, `--exclude`, `--extend-exclude`, `--force-exclude`, `--config`, `--check`, `--diff`, `-q`, `-h`, `--version` |
| Ignore  | `--fast`/`--safe`, `-W`, `--color`/`--no-color`, `-v`, `--required-version`, `--cache-dir`, `--no-cache`                                                                                                  |
| None    | `-c`/`--code`, `--pyi`, `--ipynb`, `--python-cell-magics`, `-x`, `--line-ranges`, `--stdin-filename`                                                                                                      |

Ignored options are accepted but do nothing. Rejected options change what the input is, and ignoring them would silently give different output from what you asked for.

## Configuration

Settings are read from `[tool.black]` in the project's `pyproject.toml` See [here](https://black.readthedocs.io/en/stable/usage_and_configuration/the_basics.html#where-black-looks-for-the-file) for more. Command line options override them.

E.g:

``` toml
[tool.black]
line-length = 100
skip-string-normalization = true
```

See Black's [configuration docs](https://black.readthedocs.io/en/stable/usage_and_configuration/the_basics.html#configuration-via-a-file) for every setting.

### Excluding files

`exclude` and `extend-exclude` only apply when searching directories. A file named explicitly on the command line, or opened in an editor, is still formatted. To skip a file in every case, use `force-exclude`:

``` toml
[tool.black]
force-exclude = '^/generated/'
```

## Editors

Install the `lsp` extra as well:

``` bash
pip install python-fragments[lsp,black]
```

The language server then provides document formatting. Black's options can be passed in the `fragments.blackArgs` setting, a string such as `"-l 100 --preview"`. The server requests it from the editor with `workspace/configuration` each time it formats a document, so changes apply immediately.

The setting accepts the same options as `fragments black`, with these differences:

- File paths, `-h` and `--version` are rejected.
- `--check`, `--diff` and `-q` have no effect.

**Black caches the `pyproject.toml` it reads, so restart the language server after changing `[tool.black]`.**

### VS Code

Make Python Fragments the formatter for Python files:

``` json
{
  "[python]": {
    "editor.defaultFormatter": "tra-technologies-ltd.python-fragments",
    "editor.formatOnSave": true
  },
  "fragments.blackArgs": "-l 100 --preview"
}
```

After changing `[tool.black]`, run **Python Fragments: Restart Server**.

## Pre-commit

Run Black on every commit with [pre-commit](https://pre-commit.com/).

1.  Install pre-commit:

    ``` bash
    pip install pre-commit
    ```

2.  Add the hook to `.pre-commit-config.yaml` in the root of your repository:

    ``` yaml
    repos:
      - repo: https://github.com/TheRunningAlgorithm2/python-fragments
        rev: v0.38
        hooks:
          - id: fragments-black
    ```

    Or use a local hook that runs the `fragments` already installed in your environment:

    ``` yaml
    repos:
      - repo: local
        hooks:
          - id: fragments-black
            name: fragments black
            entry: fragments black
            language: system
            types: [python]
    ```

3.  Install the git hook:

    ``` bash
    pre-commit install
    ```

4.  Optionally, format everything already in the repository:

    ``` bash
    pre-commit run fragments-black --all-files
    ```

The hook formats staged files in place. If it changes anything, the commit is stopped so you can review the changes and `git add` them. Files without fragments are formatted as normal Python, so the hook is safe to run on every `.py` file.

Pass Black options with the hook's `args:` key:

``` yaml
        hooks:
          - id: fragments-black
            args: [--line-length, "100", --preview]
```

!!! warning "Use instead of a Black hook"

    Black itself can't parse fragment syntax. Don't run a separate Black hook on the same files: `fragments-black` replaces it.

Pre-commit passes each staged file by name, so only `force-exclude` applies (see [Excluding files](#excluding-files)). You can also use pre-commit's own `exclude:` key on the hook.

### Running in CI

Use `--check` to fail without changing any files:

``` bash
fragments black --check .
```
