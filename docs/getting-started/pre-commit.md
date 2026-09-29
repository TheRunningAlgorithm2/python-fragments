# Pre-commit

Run the formatter automatically on every commit with [pre-commit](https://pre-commit.com/). Only the Python outside fragments is formatted with Black; everything inside `<>...</>` is left exactly as written.

## Setup

1. Install pre-commit:

    ```bash
    pip install pre-commit
    ```

2. Add a `.pre-commit-config.yaml` to the root of your repository.

    Reference the hook directly from this repository (available from v0.37):

    ```yaml
    repos:
      - repo: https://github.com/TheRunningAlgorithm2/python-fragments
        rev: v0.37
        hooks:
          - id: fragments-format
    ```

    Or use a local hook that runs the `fragments` already installed in your environment (requires `pip install python-fragments[format]`):

    ```yaml
    repos:
      - repo: local
        hooks:
          - id: fragments-format
            name: fragments format
            entry: fragments format
            language: system
            types: [python]
    ```

3. Install the git hook:

    ```bash
    pre-commit install
    ```

4. Optionally format everything already in the repository:

    ```bash
    pre-commit run fragments-format --all-files
    ```

## How it behaves

- The hook formats staged files in place. If it changes anything the commit is stopped so you can review the changes and `git add` them, then commit again.
- Files that fail to parse are reported as `path:line:column: message`, the remaining files are still formatted, and the commit is stopped.
- Files without fragments are formatted as normal Python, so the hook is safe to run on every `.py` file.

## Running it in CI

Use `--check` to fail without changing any files:

```bash
fragments format --check .
```

or run pre-commit itself:

```bash
pre-commit run --all-files
```

## Replacing Black

Plain Black cannot parse Fragments syntax, so don't run a separate Black hook on the same files. `fragments-format` runs Black itself on the Python around your fragments, so use it in place of a Black hook rather than alongside one.
