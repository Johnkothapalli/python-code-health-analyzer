# Adding A Rule

Rules live in `src/code_health/rules/` and inspect Python's parsed abstract syntax tree. They must
not import or execute the target project.

## Design Checklist

Before implementation, open a rule-proposal issue that explains:

- the risky or confusing pattern;
- safe and unsafe examples;
- likely false positives;
- the proposed severity; and
- why an existing Python tool does not already cover the need adequately.

Rule identifiers are public API. The next built-in identifier should be assigned during review;
do not reuse or renumber an existing identifier.

## Implementation Shape

1. Create a stateless `Rule` implementation and an AST visitor.
2. Return `Finding` objects with precise line, column, and optional symbol information.
3. Register the rule in `default_rules()`.
4. Add positive, negative, nested, and edge-case tests.
5. Document the rule in the README and changelog.

Keep messages actionable. Prefer “Replace X with Y because…” over a generic warning. If correct
behavior depends on runtime types, aliases, or data flow that the analyzer cannot resolve, narrow
the check or defer it rather than emitting a noisy result.

## Verification

```bash
ruff check .
mypy
pytest
code-health scan . --no-cache --fail-on high
```
