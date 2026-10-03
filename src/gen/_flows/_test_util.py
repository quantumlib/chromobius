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

from typing import Iterable


def assert_has_same_set_of_items_as(
        actual: Iterable,
        expected: Iterable,
        actual_name: str = 'actual',
        expected_name: str = 'expected') -> None:
    __tracebackhide__ = True

    actual = frozenset(actual)
    expected = frozenset(expected)
    if actual == expected:
        return

    lines = [f"set({actual_name}) != set({expected_name})", ""]
    if actual - expected:
        lines.append("Extra items in actual (left):")
        for d in sorted(actual - expected):
            lines.append(f'    {d}')
    if expected - actual:
        lines.append("Missing items in actual (left):")
        for d in sorted(expected - actual):
            lines.append(f'    {d}')
    raise AssertionError("\n".join(lines))
