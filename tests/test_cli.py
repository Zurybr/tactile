"""Tests for the CLI: argparse structure and the `update` subcommand.

The `update` subcommand reinstalls tactile from the latest main branch on
GitHub. It must be a recognised subcommand and must shell out to the right
installer command (uv first, pip fallback). subprocess.run is mocked so the
tests never touch the network or the real installer.
"""

from __future__ import annotations

import subprocess
from unittest import mock

import pytest

from tactile.__main__ import _run_update, build_parser, main


def test_update_subcommand_is_recognised():
    """`tactile update` parses without error and sets command='update'."""
    parser = build_parser()
    args = parser.parse_args(["update"])
    assert args.command == "update"


def test_update_prefers_uv_tool_install():
    """_run_update shells out to `uv tool install --force` from GitHub first."""
    with mock.patch("tactile.__main__.subprocess.run") as run_mock:
        _run_update()

    run_mock.assert_called_once()
    cmd = run_mock.call_args.args[0]
    assert cmd[:3] == ["uv", "tool", "install"]
    assert "--force" in cmd
    assert "git+https://github.com/Zurybr/tactile" in cmd


def test_update_falls_back_to_pip_when_uv_missing():
    """A FileNotFoundError (uv not installed) triggers the pip fallback."""
    with mock.patch("tactile.__main__.subprocess.run") as run_mock:
        run_mock.side_effect = [FileNotFoundError, None]  # uv missing, pip ok
        _run_update()

    assert run_mock.call_count == 2
    pip_cmd = run_mock.call_args_list[1].args[0]
    assert pip_cmd[1:3] == ["-m", "pip"]
    assert "--upgrade" in pip_cmd
    assert "--force-reinstall" in pip_cmd
    assert "git+https://github.com/Zurybr/tactile" in pip_cmd


def test_update_exits_nonzero_on_uv_failure():
    """A real uv failure (CalledProcessError) aborts with exit code 1."""
    with mock.patch("tactile.__main__.subprocess.run") as run_mock:
        run_mock.side_effect = subprocess.CalledProcessError(1, "uv")
        with pytest.raises(SystemExit) as exc:
            _run_update()

    assert exc.value.code == 1


def test_main_routes_update_to_run_update():
    """`tactile update` (via argv) dispatches to _run_update and returns."""
    with (
        mock.patch("tactile.__main__.sys.argv", ["tactile", "update"]),
        mock.patch("tactile.__main__._run_update") as update_mock,
    ):
        main()

    update_mock.assert_called_once()
