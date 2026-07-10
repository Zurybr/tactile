"""Command-line entry point for tactile."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from tactile import __version__

# The canonical source for reinstall: latest main branch on GitHub.
_GITHUB_SOURCE = "git+https://github.com/Zurybr/tactile"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tactile")
    parser.add_argument("--version", action="store_true", help="show version and exit")

    subparsers = parser.add_subparsers(dest="command")
    practice_parser = subparsers.add_parser("practice", help="practice typing a code/text file")
    practice_parser.add_argument("path", help="path to the file to practice")
    subparsers.add_parser(
        "update", help="update tactile to the latest version from GitHub"
    )

    return parser


def _run_update() -> None:
    """Reinstall tactile from the latest main branch on GitHub.

    Prefers ``uv tool install`` (the project's installer); if ``uv`` is not on
    PATH (``FileNotFoundError``) it falls back to ``pip install --upgrade
    --force-reinstall``. Any installer failure prints to stderr and exits 1.
    """
    print(f"tactile {__version__}")
    print("Updating from GitHub...")
    # Try uv first (preferred installer).
    try:
        subprocess.run(
            ["uv", "tool", "install", "--force", _GITHUB_SOURCE],
            check=True,
        )
    except FileNotFoundError:
        # uv not found -- fall back to pip.
        try:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--upgrade",
                    "--force-reinstall",
                    _GITHUB_SOURCE,
                ],
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            print(f"Update failed: {exc}", file=sys.stderr)
            sys.exit(1)
    except subprocess.CalledProcessError as exc:
        print(f"Update failed: {exc}", file=sys.stderr)
        sys.exit(1)

    print("Update complete. Run 'tactile --version' to verify.")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.version:
        print(f"tactile {__version__}")
        return

    if args.command == "update":
        _run_update()
        return

    from tactile.app import TactileApp

    if args.command == "practice":
        practice_path = Path(args.path)
        if not practice_path.is_file():
            print(f"tactile: file not found: {practice_path}", file=sys.stderr)
            sys.exit(1)
        TactileApp(practice_file=practice_path).run()
        return

    TactileApp().run()


if __name__ == "__main__":
    main()
