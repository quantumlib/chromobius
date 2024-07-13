import stim

from gen._layers._data import R_ZXY
from gen._layers._feedback_layer import _basis_before_rotation


def test_basis_before_rotation():
    assert _basis_before_rotation("X", R_ZXY) == "Y"
    assert _basis_before_rotation("Y", R_ZXY) == "Z"
    assert _basis_before_rotation("Z", R_ZXY) == "X"
