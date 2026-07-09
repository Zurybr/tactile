# uv

tactile uses [uv](https://docs.astral.sh/uv/) as its package manager and build
backend. All commands in this project run through `uv`.

## Why uv

| Need | uv |
|------|----|
| One tool for venv, dependencies, and build | `uv sync`, `uv add`, `uv build` — no separate `venv`/`pip`/`build` steps |
| Fast, lockfile-backed resolution | A committed `uv.lock` makes installs reproducible |
| A real build backend | `uv_build` (no need for `setuptools` or `hatchling`) |
| Dependency groups for dev deps | `[dependency-groups] dev = [...]`, installed by `uv sync` |

### Alternatives considered

- **pip + venv** — the baseline, but manual: you manage the venv, the
  lockfile (none, by default), and the build backend separately.
- **poetry** — mature, but a heavier tool with its own dependency resolver
  and a different config format (`tool.poetry` rather than standard
  `[project]`).
- **rye** — capable, but now folded into uv; uv is the actively developed
  successor.
- **pdm** — solid PEP 621 implementation, but a smaller ecosystem and
  slower than uv for cold installs.

uv was chosen for speed, the single-tool story, and first-class support for
standard `[project]` metadata.

## The build backend

`pyproject.toml` declares `uv_build` as the build backend:

```toml
[build-system]
requires = ["uv_build>=0.9.22,<0.10.0"]
build-backend = "uv_build"
```

This builds the `tactile` package from the `src/` layout and registers the
console script:

```toml
[project.scripts]
tactile = "tactile.__main__:main"
```

After `uv sync`, both `uv run tactile` and `uv run python -m tactile` work.

## Dependencies

Runtime dependencies are intentionally minimal — a single one:

```toml
[project]
dependencies = ["textual>=0.60"]
```

Development dependencies live in a dependency group, so they are not shipped
with the package:

```toml
[dependency-groups]
dev = ["pytest", "pytest-asyncio"]
```

`uv sync` installs both the runtime and dev groups into `.venv`. To install
*only* runtime dependencies (e.g. in CI for a smoke test), use
`uv sync --no-dev`.

## Lock file

`uv.lock` is committed. It pins exact versions for reproducible installs
across machines. Do not edit it by hand — let `uv` manage it via `uv add`,
`uv remove`, or `uv lock`.

## Common commands

```sh
uv sync                              # create/update .venv, install all deps
uv run tactile                       # launch the trainer
uv run tactile practice path/to/file # code practice
uv run python -m tactile --version   # prints "tactile 0.1.0"
uv run pytest -q                     # run the test suite (76 passed)
uv add <pkg>                         # add a runtime dependency
uv add --dev <pkg>                   # add a dev dependency
uv build                             # build sdist + wheel into dist/
```
