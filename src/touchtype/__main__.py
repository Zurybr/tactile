"""Command-line entry point for touchtype."""

from __future__ import annotations

import argparse

from touchtype import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="touchtype")
    parser.add_argument("--version", action="store_true", help="show version and exit")

    subparsers = parser.add_subparsers(dest="command")
    practice_parser = subparsers.add_parser("practice", help="practice typing a code/text file")
    practice_parser.add_argument("path", help="path to the file to practice")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.version:
        print(f"touchtype {__version__}")
        return

    if args.command == "practice":
        print("touchtype: TUI launch comes in a later task")
        return

    from touchtype.app import TouchTypeApp

    TouchTypeApp().run()


if __name__ == "__main__":
    main()
