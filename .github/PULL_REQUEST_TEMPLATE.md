## Summary

<!-- One or two sentences: what this PR does and why. -->

## Related issue

<!-- `Closes #123`, `Refs #456`, or "none". -->

## Type of change

- [ ] Bugfix
- [ ] Feature
- [ ] Refactor (no behaviour change)
- [ ] Documentation
- [ ] Breaking change

## Checklist

- [ ] Tests added for new/changed behaviour and `uv run pytest -q` passes
      (see [CONTRIBUTING.md](../CONTRIBUTING.md) for the strict-TDD expectation).
- [ ] Pure-logic changes (`engine`, `curriculum`, `progress`, `codeload`,
      `layouts`) do not import Textual or do I/O.
- [ ] Documentation under `docs/` updated where behaviour changed.
- [ ] `CHANGELOG.md` has an entry under `[Unreleased]` for user-facing changes.
- [ ] Commits follow [Conventional Commits](https://www.conventionalcommits.org/)
      (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`); no AI attribution.
- [ ] `pyproject.toml` version and `src/tactile/__init__.py` `__version__`
      are in sync (if this is a release).

## Notes for the reviewer

<!-- What to review first, what is intentionally out of scope, anything that
     needs a judgment call. -->
