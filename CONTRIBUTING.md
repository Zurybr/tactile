# Contributing to tactile

Thanks for your interest in improving **tactile**. This guide is short and
practical — read it once and you should be ready to send a pull request.

## Quick path

1. Clone the repo and sync dependencies: `uv sync`.
2. Run the test suite: `uv run pytest -q` (should report **76 passed**).
3. Make your change with a test, see it fail, implement, see it pass.
4. Commit using a [conventional commit](https://www.conventionalcommits.org/)
   message.
5. Open a pull request against `main`.

## Setting up

tactile requires **Python >= 3.12** and **[uv](https://docs.astral.sh/uv/)**.

```sh
git clone <your-fork-url>
cd tactile
uv sync                 # creates .venv and installs tactile + dev deps
uv run pytest -q        # 76 passed
uv run tactile          # launches the trainer
```

Dev dependencies (`pytest`, `pytest-asyncio`) live in the `dev` dependency
group in `pyproject.toml`; `uv sync` installs them automatically.

## The testing expectation (strict TDD)

tactile was built with strict test-driven development, and that is the
expected workflow for any change to the pure-logic modules
(`engine.py`, `curriculum.py`, `progress.py`, `codeload.py`, `layouts/`):

1. **Red** — write the failing test first. Run it and watch it fail for the
   right reason (module missing, assertion wrong).
2. **Green** — implement the minimum code to make it pass.
3. **Refactor** — clean up while keeping the tests green.

For the Textual UI, drive behaviour with `Pilot` tests (see
[docs/engineering/testing.md](docs/engineering/testing.md)). Every new screen
or binding should have at least one Pilot test covering the happy path.

If you add a feature, add a test. If you fix a bug, add a test that reproduces
it first. PRs that drop test coverage will be asked to add tests before merge.

## Code style

- English for all code, comments, identifiers, and UI copy.
- `from __future__ import annotations` at the top of every module (the
  existing code does this).
- Pure-logic modules (`engine`, `curriculum`, `progress`, `codeload`,
  `layouts`) must not import Textual or do I/O — keep them testable in
  isolation.
- Keep functions small and named after what they do.
- No "Co-Authored-By" or AI-attribution lines in commits.

## Commit messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add dvorak layout data
fix: stop cursor advancing on wrong key in code practice
docs: document the progress JSON schema
refactor: extract star-threshold constants
chore: bump textual to 0.61
```

- One logical change per commit.
- The subject line is lowercase, imperative, and short.
- Add a body only when the "why" is not obvious from the subject.

## Branches and pull requests

- Branch from `main`: `feat/<short-description>`, `fix/<short-description>`,
  `docs/<short-description>`.
- Keep PRs focused — one feature or one fix. Use the
  [pull request template](.github/PULL_REQUEST_TEMPLATE.md).
- Make sure `uv run pytest -q` is green before requesting review.
- Update [CHANGELOG.md](CHANGELOG.md) under an `[Unreleased]` section for
  user-facing changes.
- Update documentation under [docs/](docs/) when behaviour changes.

## Adding a new layout or wordlist

See [docs/engineering/development.md](docs/engineering/development.md) for the
step-by-step. The short version: add a `layouts/<id>.py` with a `Layout`
built from `build_char_map` (+ `add_dead_key_vowels` for dead keys), register
it in `LAYOUTS`, add a wordlist under `wordlists/`, and cover it with tests in
`tests/test_layouts.py`.

## Code of conduct

By participating you agree to uphold the
[Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). Be kind.

## Questions?

Open a [GitHub issue](https://github.com/) with the `question` label, or
email the maintainer at **brandom.ledesma@hotmail.com**.
