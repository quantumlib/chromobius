from typing import Literal

import numpy as np

R_XYZ = 0
R_XZY = 1
R_YXZ = 2
R_YZX = 3
R_ZXY = 4
R_ZYX = 5
PERMUTATIONS: list[dict[Literal["X", "Y", "Z"], Literal["X", "Y", "Z"]]] = [
    {"X": "X", "Y": "Y", "Z": "Z"},
    {"X": "X", "Y": "Z", "Z": "Y"},
    {"X": "Y", "Y": "X", "Z": "Z"},
    {"X": "Y", "Y": "Z", "Z": "X"},
    {"X": "Z", "Y": "X", "Z": "Y"},
    {"X": "Z", "Y": "Y", "Z": "X"},
]
INVERSE_PERMUTATIONS: list[dict[Literal["X", "Y", "Z"], Literal["X", "Y", "Z"]]] = [
    {"X": "X", "Y": "Y", "Z": "Z"},
    {"X": "X", "Y": "Z", "Z": "Y"},
    {"X": "Y", "Y": "X", "Z": "Z"},
    {"X": "Z", "Y": "X", "Z": "Y"},
    {"X": "Y", "Y": "Z", "Z": "X"},
    {"X": "Z", "Y": "Y", "Z": "X"},
]
ORIENTATIONS = [
    "I",
    "SQRT_X",
    "S",
    "C_XYZ",
    "C_ZYX",
    "H",
]
ORIENTATION_MULTIPLICATION_TABLE = np.array(
    [
        [0, 1, 2, 3, 4, 5],
        [1, 0, 4, 5, 2, 3],
        [2, 3, 0, 1, 5, 4],
        [3, 2, 5, 4, 0, 1],
        [4, 5, 1, 0, 3, 2],
        [5, 4, 3, 2, 1, 0],
    ],
    dtype=np.uint8,
)
