"""Command-line entry point for tactile."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
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

    On Windows, launches a detached updater batch script because the
    running executable's directory cannot be removed while tactile is
    active (Access is denied, os error 5).  On Unix, runs the update
    directly (Unix allows overwriting running executables).

    Prefers ``uv tool install``; falls back to ``pip`` if ``uv`` is not
    on ``PATH``.  Any installer failure prints to stderr and exits 1.
    """
    print(f"tactile {__version__}")

    if os.name == "nt":
        _update_windows()
        return  # _update_windows calls sys.exit

    # -- Unix: direct self-update --
    print("Updating from GitHub...")
    _try_uv_or_pip()
    print("Update complete. Run 'tactile --version' to verify.")


def _try_uv_or_pip() -> None:
    """Attempt the reinstall via uv, falling back to pip."""
    try:
        subprocess.run(
            ["uv", "tool", "install", "--force", _GITHUB_SOURCE],
            check=True,
        )
    except FileNotFoundError:
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


def _update_windows() -> None:
    """Launch a detached batch updater on Windows.

    Windows locks the executable of a running process, so ``uv`` cannot
    remove the tool directory while tactile is active.  This method writes
    a temporary ``.bat`` file that waits a few seconds for tactile to exit,
    runs ``uv tool install --force``, prints the result, and then deletes
    itself.
    """
    bat = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".bat",
        delete=False,
        dir=os.environ.get("TEMP", "."),
    )
    bat.write(
        "@echo off\n"
        "echo.\n"
        "echo Waiting for tactile to close...\n"
        "timeout /t 3 /nobreak >nul\n"
        "echo Updating tactile from GitHub...\n"
        f'uv tool install --force "{_GITHUB_SOURCE}"\n'
        "if %ERRORLEVEL% EQU 0 (\n"
        "    echo.\n"
        "    echo Update complete! Run 'tactile --version' to verify.\n"
        ") else (\n"
        "    echo.\n"
        "    echo Update failed. Try manually:\n"
        f'    echo   uv tool install --force "{_GITHUB_SOURCE}"\n'
        ")\n"
        "echo.\n"
        "pause\n"
        'del "%~f0"\n'
    )
    bat.close()

    # Launch in a new console window so the user sees the output.
    subprocess.Popen(
        ["cmd", "/c", bat.name],
        creationflags=subprocess.CREATE_NEW_CONSOLE,
        close_fds=True,
    )

    print("Updater launched in a new window.")
    print("tactile will close now and the updater will finish in a few seconds.")
    sys.exit(0)


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
