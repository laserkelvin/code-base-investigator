# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import io
import json
import logging
import sys
import tempfile
import unittest
import warnings
from contextlib import redirect_stdout
from pathlib import Path

from codebasin.coverage.__main__ import cli


class TestCbicov(unittest.TestCase):
    """
    Test cbicov command line interface.
    """

    def setUp(self):
        logging.disable()
        warnings.simplefilter("ignore", ResourceWarning)

    def test_help(self):
        """Check help string displays correctly."""

        # Supplying no commands displays the help string.
        with self.assertRaises(SystemExit) as e:
            with redirect_stdout(io.StringIO()) as f:
                cli([])
        self.assertEqual(e.exception.code, 2)
        self.assertRegex(f.getvalue(), "usage:")

        # Supplying -h or --help displays the help string.
        for option in ["-h", "--help"]:
            with self.subTest(option=option):
                with self.assertRaises(SystemExit) as e:
                    with redirect_stdout(io.StringIO()) as f:
                        cli([option])
                self.assertEqual(e.exception.code, 0)
                self.assertRegex(f.getvalue(), "usage:")

        # Supplying a command with -h or --help displays the help string.
        for command in ["compute"]:
            for option in ["-h", "--help"]:
                with self.subTest(command=command, option=option):
                    with self.assertRaises(SystemExit) as e:
                        with redirect_stdout(io.StringIO()) as f:
                            cli([command, option])
                    self.assertEqual(e.exception.code, 0)
                    self.assertRegex(f.getvalue(), "usage:")

    def test_path_validation(self):
        """Check that path arguments are validated."""
        sys.stdout = io.StringIO()
        for path in ["invalid\npath", "invalid.extension"]:
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    cli(["compute", path])
                    cli(["compute", "-o", path])
        sys.stdout = sys.__stdout__

    def test_compute(self):
        """Check that coverage is computed correctly."""
        sys.stdout = io.StringIO()
        # Create a temporary codebase to work on.
        self.tmp = tempfile.TemporaryDirectory()
        p = Path(self.tmp.name)
        with open(p / "foo.cpp", mode="w") as f:
            f.write(
                r"""#ifdef MACRO
            void guarded();
            #endif
            unguarded();""",
            )
        with open(p / "bar.h", mode="w") as f:
            f.write("unguarded();")

        # cbicov reads compile commands from disk.
        compile_commands = [
            {
                "file": str(p / "foo.cpp"),
                "command": "c++ foo.cpp",
            },
            {
                "file": str(p / "bar.cpp"),
                "command": "c++ bar.cpp",
            },
        ]
        with open(p / "compile_commands.json", mode="w") as f:
            json.dump(compile_commands, f)

        ipath = p / "compile_commands.json"
        opath = p / "coverage.json"
        with self.assertRaises(SystemExit):
            cli(["compute", "-S", str(p), "-o", str(opath), str(ipath)])

        with open(p / "coverage.json") as f:
            coverage = json.load(f)
        expected_coverage = [
            {
                "file": "bar.h",
                "id": "3ba8372282f8f1bafc59bb3d0472dcd7ecd5f13a54f17585c6012bfc40bfba7b9afb905f24ccea087546f4c90363bba97d988e4067ec880f619d0ab623c3a7a1",  # noqa: E501
                "lines": [1],
            },
            {
                "file": "foo.cpp",
                "id": "1359957a144db36091624c1091ac6a47c47945a3ff63a47ace3dc5c1b13159929adac14c21733ec1054f7f1f8809ac416e643483191aab6687d7849ee17edaa0",  # noqa: E501
                "lines": [1, 2, 3, 4],
            },
        ]
        self.assertEqual(coverage, expected_coverage)
        sys.stdout = sys.__stdout__


if __name__ == "__main__":
    unittest.main()
