#!/usr/bin/env python3
# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Produces a .pyi file for chromobius, describing the contained classes and functions.
"""

import chromobius
import sys

from util_gen_stub_file import generate_documentation


def main():
    version = chromobius.__version__
    if "dev" in version or version == "VERSION_INFO" or "-dev" in sys.argv:
        version = "(Development Version)"
    else:
        version = "v" + version
    print(f'''
"""Chromobius {version}: an implementation of the mobius color code decoder."""
# (This a stubs file describing the classes and methods in stim.)
from __future__ import annotations
from typing import overload, TYPE_CHECKING, Any, Iterable
if TYPE_CHECKING:
    import io
    import pathlib
    import numpy as np
    import stim
    import sinter
    import chromobius
__version__: str
'''.strip())

    for obj in generate_documentation(obj=chromobius, full_name="chromobius", level=-1):
        text = '\n'.join(("    " * obj.level + line).rstrip()
                        for paragraph in obj.lines
                        for line in paragraph.splitlines())
        assert "stim::" not in text, "CONTAINS C++ STYLE TYPE SIGNATURE!!:\n" + text
        print(text)


if __name__ == '__main__':
    main()
