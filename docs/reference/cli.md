# CLI

tactile is invoked through the `tactile` console script or `python -m tactile`.
The entry point is `tactile.__main__:main`, built on `argparse`.

## Commands

```
tactile [--version]
tactile practice <path>
tactile update
```

| Command | Behaviour |
|---------|-----------|
| `tactile` | Launch the trainer. On first run (no active layout) shows the layout select screen; otherwise opens the lesson map for the active layout. |
| `tactile practice <path>` | Jump straight into code practice for `<path>`. Uses the active layout, or `en_us` if no layout is set yet. The lesson map is underneath so `escape`/results navigation still works. |
| `tactile update` | Reinstall tactile from the latest `main` branch on GitHub (`git+https://github.com/Zurybr/tactile`). Prefers `uv tool install --force`; falls back to `pip install --upgrade --force-reinstall` if `uv` is not on PATH. Exits `1` if the installer fails. |
| `tactile --version` | Print `tactile <version>` (e.g. `tactile 0.1.0`) and exit. |

`python -m tactile` is equivalent to `tactile` and accepts the same
arguments.

## Flags

| Flag | Effect |
|------|--------|
| `--version` | Print `tactile 0.1.0` to stdout and exit 0. Checked before any subcommand. |

There are no global flags beyond `--version`.

## The `practice` subcommand

```
tactile practice path/to/file.py
```

- `<path>` is required and must be an existing file.
- If the path does not exist or is not a file, tactile prints
  `tactile: file not found: <path>` to **stderr** and exits **1**.
- The file is processed by `load_code_exercises` (utf-8 with latin-1
  fallback, tabs → 4 spaces, leading/trailing whitespace stripped, 2000-line
  cap, untypable chars removed with a notice) and chunked into 10-line
  exercises.
- Code-practice results are shown but not recorded as lesson progress; only
  the key-error heatmap accumulates.

## The `update` subcommand

```
tactile update
```

- Reinstalls tactile from the latest `main` branch on GitHub
  (`git+https://github.com/Zurybr/tactile`). No local checkout is needed —
  the installer fetches and builds directly from the git URL.
- Prints `tactile <version>` then `Updating from GitHub...` before running the
  installer. On success it prints
  `Update complete. Run 'tactile --version' to verify.`
- **Installer selection**: prefers `uv tool install --force` (the project's
  installer). If `uv` is not on PATH (`FileNotFoundError`), it falls back to
  `python -m pip install --upgrade --force-reinstall`.
- **Failure**: if the chosen installer exits non-zero
  (`subprocess.CalledProcessError`), tactile prints `Update failed: <exc>` to
  **stderr** and exits **1**. `FileNotFoundError` from `uv` is NOT treated as
  a failure — it triggers the pip fallback.
- Requires network access (it clones from GitHub). Does not touch the
  progress store; only the installed package changes.

## Version source

The version comes from `tactile.__version__` in `src/tactile/__init__.py`,
which must match `version` in `pyproject.toml`. See
[engineering/release.md](../engineering/release.md#the-version-number).

## The argparse definition

For reference, the parser is built in `__main__.py`:

```python
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tactile")
    parser.add_argument("--version", action="store_true", help="show version and exit")

    subparsers = parser.add_subparsers(dest="command")
    practice_parser = subparsers.add_parser("practice", help="practice typing a code/text file")
    practice_parser.add_argument("path", help="path to the file to practice")
    subparsers.add_parser("update", help="update tactile to the latest version from GitHub")
    return parser
```

`--version` is handled before the app is imported, so `tactile --version`
works even if a GUI dependency would fail to load. `tactile update` likewise
returns before importing `TactileApp`, so it works without a usable display.
