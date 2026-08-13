# Roadmap

This roadmap communicates direction rather than promising dates. Design discussion should happen
in public issues before implementation.

## Current: 0.1

- Dependency-free AST analysis without importing target code.
- Text, JSON, and SARIF output.
- Complexity metrics, import-cycle detection, caching, and concurrent scanning.
- CI across supported Python versions and operating systems.

## Near Term

- Read configuration from `pyproject.toml`.
- Support per-rule selection and suppression with auditable output.
- Add path and glob exclusions beyond directory-name exclusions.
- Improve import resolution for namespace packages and `src` layouts.
- Publish signed source and wheel distributions.

## Later

- Analyze only files changed in a Git comparison.
- Document a stable third-party rule interface.
- Add data-flow-aware checks where they can remain explainable.
- Establish performance benchmarks on representative public projects.

See the issue tracker for scoped work that is ready for contribution. New roadmap items should
describe the user problem and tradeoffs rather than only proposing a technology.
