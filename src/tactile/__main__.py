"""Command-line entry point for tactile."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tactile import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tactile")
    parser.add_argument("--version", action="store_true", help="show version and exit")

    subparsers = parser.add_subparsers(dest="command")
    practice_parser = subparsers.add_parser("practice", help="practice typing a code/text file")
    practice_parser.add_argument("path", help="path to the file to practice")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.version:
        print(f"tactile {__version__}")
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
