# Contributing to Python Fragments

Thanks for your interest in Python Fragments! We're actively working toward a stable v1 release and genuinely value community involvement, even if code contributions aren't open just yet.

## Reporting bugs

If you've found something that doesn't behave as expected, please open a [GitHub Issue](https://github.com/TheRunningAlgorithm2/python-fragments/issues/new?template=bug_report.yml) using the bug report template. Try to include:

- A minimal, self-contained example that reproduces the problem
- The Python version and `python-fragments` version you are using
- What you expected to happen and what actually happened

## Requesting features

If there's something you'd like to see in Python Fragments, open a [GitHub Issue](https://github.com/TheRunningAlgorithm2/python-fragments/issues) and describe the use case or problem you're trying to solve. Framing the problem rather than jumping straight to a proposed solution helps us understand the need and find the best approach.

## Documentation corrections

Spotted something unclear, incomplete, or wrong in the docs? Please open a [GitHub Issue](https://github.com/TheRunningAlgorithm2/python-fragments/issues/new?template=documentation.yml) using the documentation template. Good documentation is important to us and flagging issues is a great way to help even before v1.

## Development setup

We encourage anyone interested to explore the codebase. To get it running locally:

```bash
git clone https://github.com/TheRunningAlgorithm2/python-fragments.git
cd python-fragments
python -m venv venv
source venv/bin/activate
pip install -e ".[dev,lsp]"
```

Run the test suite:

```bash
python -m pytest tests/ -v
```

## What's coming after v1

Code contributions aren't open yet. We're using Python Fragments internally at The Running Algorithm and are still settling on what we want the syntax and API to look like before we commit to a stable interface. Once we reach v1 and are happy with the foundations, we plan to open up contributions fully.

In the meantime, bug reports, feature requests, and documentation feedback are all genuinely useful and help shape where v1 lands.
