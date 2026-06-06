# Roadmap

Python Fragments is pre-v1 and under active development at [The Running Algorithm](https://www.therunningalgorithm.com). This page outlines what we're working toward.

## Before v1

The focus before v1 is not features: it's foundations. We're using Python Fragments in production internally and working to settle on a concrete developer experience and stable API before making any commitments. Until v1, the syntax and API may change between releases.

## After v1

Once the foundations are solid, we plan to invest heavily in tooling:

- **Black and Ruff formatter support**: fragment syntax should format cleanly without requiring workarounds
- **isort and Ruff import sorting**: imports in fragment files should sort correctly alongside regular Python
- **Linter compatibility**: fragment syntax should not produce false positives in common linters
- **Better error messages**: transpiler errors should point to the original fragment source, not the transpiled output

## Staying up to date

Watch the [GitHub repository](https://github.com/TheRunningAlgorithm2/python-fragments) for updates.
