# CLI

tactile is invoked through the `tactile` console script or `python -m tactile`.
The entry point is `tactile.__main__:main`, built on `argparse`.

## Commands

```
tactile [--version]
tactile practice <path>
```

| Command | Behaviour |
|---------|-----------|
| `tactile` | Launch the trainer. On first run (no active layout) shows the layout select screen; otherwise opens the lesson map for the active layout. |
| `tactile practice <path>` | Jump straight into code practice for `<path>`. Uses the active layout, or `en_us` if no layout is set yet. The lesson map is underneath so `escape`/results navigation still works. |
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
    return parser
```

`--version` is handled before the app is imported, so `tactile --version`
works even if a GUI dependency would fail to load.
