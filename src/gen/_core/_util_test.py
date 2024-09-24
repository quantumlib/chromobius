import pytest

from gen._core._util import min_max_complex, sorted_complex


def test_sorted_complex():
    assert sorted_complex([1, 2j, 2, 1 + 2j]) == [2j, 1, 1 + 2j, 2]


def test_min_max_complex():
    with pytest.raises(ValueError):
        min_max_complex([])
    assert min_max_complex([], default=0) == (0, 0)
    assert min_max_complex([], default=1 + 2j) == (1 + 2j, 1 + 2j)
    assert min_max_complex([1j], default=0) == (1j, 1j)
    assert min_max_complex([1j, 2]) == (0, 2 + 1j)
    assert min_max_complex([1j + 1, 2]) == (1, 2 + 1j)
