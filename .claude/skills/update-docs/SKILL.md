---
name: update-docs
description: Check over the docs and make necessary updates.
allowed-tools: Bash(git diff*) Bash(find *) Bash(xargs cat)
---

# Context

1. Current git diff !`git diff`
2. All docs files !`find ./docs -type f -name "*.md"`
3. All the docs content !`find ./docs -type f -name "*.md" | xargs cat`

# Introduction

The supplied context contains all of the current changes. Look through them, and then update the docs with anything that needs to be changed as per the latest set of changes.

Make the following additional checks:

1. Check that `docs/benchmarks/index.md` is up to date - re-calculate if necessary
