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
