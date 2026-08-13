# Changelog

All notable user-facing changes are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and releases use
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

## 0.1.0 - 2026-08-13

### Added

- Initial analyzer with six findings covering parse failures, mutable defaults, unsafe calls,
  broad exception handling, blocking calls in async functions, and complexity thresholds.
- Text, JSON, and SARIF reporters.
- Import-cycle detection, SQLite caching, concurrent scanning, and typed public models.
- Repeated `--exclude-dir NAME` options for project-specific generated and vendored directories.
- Distribution build and metadata validation in continuous integration.
- Contributor, support, security, governance, and roadmap documentation.
