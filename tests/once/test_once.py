# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import unittest
from pathlib import Path

from codebasin import CodeBase, finder
from codebasin.walkers.platform_mapper import PlatformMapper


class TestOnce(unittest.TestCase):
    """
    Simple test of ability to obey #pragma once directives.
    """

    def setUp(self):
        self.rootdir = Path(__file__).parent.resolve()
        logging.getLogger("codebasin").disabled = True

        self.expected_setmap = {
            frozenset([]): 4,
            frozenset(["CPU", "GPU"]): 10,
        }

    def test_yaml(self):
        """once/once.yaml"""
        codebase = CodeBase(self.rootdir)
        configuration = {
            "CPU": [
                {
                    "file": str(self.rootdir / "main.cpp"),
                    "defines": ["CPU"],
                    "include_paths": [],
                    "include_files": [],
                },
            ],
            "GPU": [
                {
                    "file": str(self.rootdir / "main.cpp"),
                    "defines": ["GPU"],
                    "include_paths": [],
                    "include_files": [],
                },
            ],
        }
        state = finder.find(str(self.rootdir), codebase, configuration)
        mapper = PlatformMapper(codebase)
        setmap = mapper.walk(state)
        self.assertDictEqual(
            setmap,
            self.expected_setmap,
            "Mismatch in setmap",
        )


if __name__ == "__main__":
    unittest.main()
