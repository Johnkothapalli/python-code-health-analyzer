# Releasing

Releases are built from version tags and published through GitHub Actions. Do not upload a
distribution from a maintainer workstation or store a PyPI API token in GitHub.

## One-time PyPI setup

Before the first PyPI upload, create a pending GitHub publisher in the
[PyPI publishing settings](https://pypi.org/manage/account/publishing/) with these exact values:

- PyPI project name: `python-code-health-analyzer`
- GitHub owner: `Johnkothapalli`
- GitHub repository: `python-code-health-analyzer`
- Workflow filename: `publish-pypi.yml`
- Environment name: `pypi`

The pending publisher creates the project on the first successful upload; it does not reserve the
name before then. The `pypi` GitHub environment is an additional approval boundary for publishing.

## Release checklist

1. Update the version in `pyproject.toml` and add the release notes to `CHANGELOG.md` in a pull
   request.
2. Merge the release pull request after CI passes.
3. Create and publish a GitHub release whose tag is exactly `v` followed by the package version.
4. Confirm the release-artifact and PyPI-publish workflows both build the same tag successfully.
5. Verify the project page and install the published wheel in a clean virtual environment.

For the existing `v0.1.0` release, complete the one-time PyPI setup and manually run the
`Publish package to PyPI` workflow with `v0.1.0`. Future published GitHub releases trigger it
automatically.

The publishing job uses OpenID Connect and requests `id-token: write` only after a separate build
job has produced and validated the distributions. The tag must match the package version before
the protected publishing job can begin.
