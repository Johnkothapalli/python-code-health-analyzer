# Contributing

Thank you for improving Python Code Health Analyzer. Contributions should make the analyzer
more accurate, useful, or approachable without overstating what static analysis can prove.

## Before You Start

- Search existing issues and pull requests before opening a duplicate.
- Small fixes and tests can go directly to a pull request.
- Open an issue before adding a rule, changing report schemas, or introducing a dependency.
- Never include proprietary source code, credentials, or security-sensitive samples.

## Development Setup

Python 3.11 or newer is required.

```bash
git clone https://github.com/Johnkothapalli/python-code-health-analyzer.git
cd python-code-health-analyzer
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Run the complete local gate before submitting a pull request:

```bash
ruff check .
mypy
pytest
code-health scan . --no-cache --fail-on high
python -m build
python -m twine check dist/*
```

## Making A Change

1. Fork the repository and create a focused branch.
2. Add or update tests for observable behavior.
3. Update user documentation when flags, output, or rules change.
4. Add an entry under `Unreleased` in `CHANGELOG.md` for user-visible changes.
5. Open a pull request explaining the problem, solution, and verification performed.

Keep commits reviewable and avoid unrelated formatting or dependency churn. Maintainers may ask
for a change to be split when independent behavior is combined in one pull request.

## Adding A Rule

Read [docs/adding-a-rule.md](docs/adding-a-rule.md). A new rule needs a stable identifier, a
clear severity rationale, positive and negative tests, and wording that tells a user what to do.
Rules should avoid executing or importing the target project.

## Review Expectations

CI must pass before merge. Review considers correctness, false-positive risk, performance,
backward compatibility, test quality, and documentation. Submission does not guarantee merge;
maintainers may close changes that do not fit the project scope.

By contributing, you agree that your contribution is licensed under the repository's MIT license
and that you will follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
