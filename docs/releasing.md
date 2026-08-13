# Releasing

Releases are maintainer operations. Never publish from an uncommitted or unreviewed tree.

## Prepare

1. Move entries from `Unreleased` into a dated version section in `CHANGELOG.md`.
2. Update the version in `pyproject.toml`, `src/code_health/__init__.py`, and the CLI version flag.
3. Run the full contributor verification commands.
4. Build and inspect the distributions:

   ```bash
   python -m build
   python -m twine check dist/*
   ```

5. Merge the release pull request after CI passes.

## Publish

Create a GitHub release whose tag matches the package version, for example `v0.1.0`. The release
workflow builds the source distribution and wheel, validates them, and attaches them to the GitHub
release.

PyPI publication is intentionally not automated yet. After the initial GitHub release is reviewed,
add trusted publishing in a separate change with a protected `pypi` environment and least-privilege
OIDC job. Do not store a long-lived PyPI API token in repository secrets.

After publication, install into a clean environment and verify `code-health --version` and a small
scan before announcing the release.
