# Release

How tactile versions, changelogs, and ships a release. The project follows
[Semantic Versioning](https://semver.org/) and
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## Versioning

tactile uses `MAJOR.MINOR.PATCH`:

- **PATCH** (`0.1.0` → `0.1.1`): backwards-compatible bug fixes.
- **MINOR** (`0.1.0` → `0.2.0`): backwards-compatible new features
  (a new layout, a new screen, a new CLI flag).
- **MAJOR** (`0.x` → `1.0`): incompatible changes (a breaking CLI change,
  a progress-schema migration that drops old data).

While the project is `0.x`, minor bumps may include small breaking changes —
note them in the changelog. Once `1.0` is cut, SemVer applies strictly.

## The version number

There is exactly one source of truth: `pyproject.toml`.

```toml
[project]
version = "0.1.0"
```

`src/tactile/__init__.py` also defines `__version__ = "0.1.0"`, which the
CLI's `--version` reads. **Keep these two in sync** when you bump. The
check:

```sh
uv run python -m tactile --version   # must match pyproject.toml
```

## The changelog

[`CHANGELOG.md`](../../CHANGELOG.md) follows Keep a Changelog. Keep an
`[Unreleased]` section at the top while developing, and move it under a
dated heading at release time:

```markdown
## [Unreleased]

## [0.1.0] - 2026-07-09
...
```

Use `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`
subsections as appropriate. Link the version headings to the Keep a
Changelog site at the bottom of the file (this is already done).

## Cutting a release

1. **Make sure `main` is green.**
   ```sh
   uv run pytest -q
   uv run python -m tactile --version
   ```
2. **Bump the version** in *both* `pyproject.toml` and
   `src/tactile/__init__.py`, keeping them identical.
3. **Finalize the changelog.** Move `[Unreleased]` under a new
   `## [x.y.z] - YYYY-MM-DD` heading; start a fresh `[Unreleased]` above it.
4. **Commit.**
   ```sh
   git add pyproject.toml src/tactile/__init__.py CHANGELOG.md
   git commit -m "chore: release 0.1.0"
   ```
5. **Tag.** Use an annotated tag named `v<x.y.z>`:
   ```sh
   git tag -a v0.1.0 -m "Release 0.1.0"
   git push origin main --tags
   ```
6. **(Optional) build distributions.**
   ```sh
   uv build     # writes dist/tactile-<ver>*.tar.gz and *.whl
   ```

## After a release

- The GitHub release notes can mirror the changelog section for that
  version.
- Any hotfix goes on a patch release: bump PATCH, add a `Fixed` entry, tag
  `v<x.y.(z+1)>`.
