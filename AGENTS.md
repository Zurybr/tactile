# AGENTS.md — Working on tactile

This file gives AI agents and human contributors the conventions for working
on the tactile codebase. Follow it for **every** change.

## Stack

- Python >=3.12, [uv](https://docs.astral.sh/uv/) (package manager + `uv_build`
  backend), [Textual](https://textual.textualize.io/) >=0.60, pytest +
  pytest-asyncio.
- Run tests: `uv run pytest -q`.
- Run the app: `uv run tactile`.

## Documentation sync (MANDATORY)

Every code change MUST be reflected in the documentation. Each module maps to
a doc — update the matching doc when you touch the module:

| Module / area                  | Doc to update                          |
|--------------------------------|----------------------------------------|
| `engine.py`                    | `docs/engineering/engine.md`           |
| `curriculum.py`, `wordlists/`  | `docs/engineering/curriculum.md`       |
| `progress.py`                  | `docs/engineering/progress.md`         |
| `app.py`, `screens/`, `widgets`| `docs/engineering/tui-screens.md`      |
| `layouts/`                     | `docs/engineering/layouts.md`          |
| `codeload.py`, `file_picker`   | `docs/engineering/tui-screens.md`      |
| `__main__.py` (CLI)            | `docs/reference/cli.md`                |
| keybindings                    | `docs/reference/keybinds.md`           |
| progress JSON schema           | `docs/reference/progress-schema.md`    |
| new layout or framework choice | `docs/project/` + relevant `engineering/` |

If you add a new module, create its doc and add a wikilink entry in
`docs/index.md`. Never leave a code change without a doc update.

## Changelog sync (MANDATORY)

Every commit that changes behavior MUST add an entry to `CHANGELOG.md` under
the `[Unreleased]` section, classified by [Keep a Changelog](https://keepachangelog.com)
category:

- **Added** — new features.
- **Changed** — changes to existing functionality.
- **Deprecated** — soon-to-be removed features.
- **Removed** — removed features.
- **Fixed** — bug fixes.
- **Security** — vulnerability fixes.

Group entries under the right heading. Use imperative mood ("Add ...",
"Fix ..."). When you cut a release, move `[Unreleased]` to a versioned
section `[0.x.0] - YYYY-MM-DD` and start a fresh `[Unreleased]` on top.

## Commit classification

Use [Conventional Commits](https://www.conventionalcommits.org), and scope
each commit to the area it touches so the history reads as a
feature-classified log:

```
<type>(<scope>): <subject>
```

- **type**: `feat` | `fix` | `docs` | `refactor` | `perf` | `test` | `chore` | `ci`
- **scope** (the feature classification): `engine` | `curriculum` | `progress` |
  `tui` | `layouts` | `cli` | `docs` | `build` | `test` | `progress`
- Examples:
  - `feat(curriculum): add numbers unit to en_us`
  - `fix(progress): handle corrupt JSON without crash`
  - `docs(tui): document screen navigation pattern`
  - `refactor(engine): extract star rating thresholds`

The scope IS the feature classification. Keep commits atomic: one logical
change per commit. This makes the changelog and the git log tell the same
story.

## Docs validation (before push)

Before pushing, validate that `docs/index.md` exists and every Obsidian
wikilink in it resolves to a real file:

```sh
uv run python scripts/validate_docs.py
```

The script parses `[[path|alias]]` and `[[path]]` wikilinks from
`docs/index.md` and checks that each path points to an existing file under
`docs/`. Fix any broken link before pushing. Never push with a broken docs
index.

## Testing

Strict TDD is the project norm: red → green → refactor. Add or update a test
for every behavior change. `uv run pytest -q` must be green before commit.

## Before you push (checklist)

1. `uv run pytest -q` is green.
2. Docs for every touched module are updated (see the mapping above).
3. `CHANGELOG.md` has an entry under `[Unreleased]` for behavior changes.
4. `uv run python scripts/validate_docs.py` passes (no broken wikilinks).
5. Commit message follows `<type>(<scope>): <subject>`.
