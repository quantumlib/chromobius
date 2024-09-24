from typing import Callable, Literal, TYPE_CHECKING, cast, Iterable, Dict, Any, Union

import stim

from gen._core._util import sorted_complex

if TYPE_CHECKING:
    import gen
    from gen._core import KeyedPauliString


_multiplication_table: dict[Literal['X', 'Y', 'Z'] | None, dict[Literal['X', 'Y', 'Z'] | None, Literal['X', 'Y', 'Z'] | None]] = {
    None: {None: None, "X": "X", "Y": "Y", "Z": "Z"},
    "X": {None: "X", "X": None, "Y": "Z", "Z": "Y"},
    "Y": {None: "Y", "X": "Z", "Y": None, "Z": "X"},
    "Z": {None: "Z", "X": "Y", "Y": "X", "Z": None},
}


class PauliString:
    """A qubit-to-pauli mapping."""

    def __init__(
            self,
            mapping: Union[dict[complex, Literal["X", "Y", "Z"]],  dict[Literal["X", "Y", "Z"], complex | Iterable[complex]], 'PauliString', 'KeyedPauliString', None] = None,
            *,
            xs: Iterable[complex] = (),
            ys: Iterable[complex] = (),
            zs: Iterable[complex] = (),
    ):
        self.qubits: dict[complex, Literal["X", "Y", "Z"]] = {}

        from gen._core import KeyedPauliString
        if isinstance(mapping, (PauliString, KeyedPauliString)) and not xs and not ys and not zs:
            self.qubits = dict(mapping.qubits)
            self._hash = mapping._hash if isinstance(mapping, PauliString) else mapping.pauli_string._hash
            return

        for q in xs:
            self._mul_term(q, 'X')
        for q in ys:
            self._mul_term(q, 'Y')
        for q in zs:
            self._mul_term(q, 'Z')
        if mapping is not None:
            if isinstance(mapping, (PauliString, KeyedPauliString)):
                mapping = mapping.qubits
            for k, v in mapping.items():
                if isinstance(k, str):
                    assert k == 'X' or k == 'Y' or k == 'Z'
                    b = cast(Literal['X', 'Y', 'Z'], k)
                    if isinstance(v, (int, float, complex)):
                        self._mul_term(v, b)
                    else:
                        for q in v:
                            assert isinstance(q, (int, float, complex))
                            self._mul_term(q, b)
                elif isinstance(v, str):
                    assert v == 'X' or v == 'Y' or v == 'Z'
                    assert isinstance(k, (int, float, complex))
                    b = cast(Literal['X', 'Y', 'Z'], v)
                    self._mul_term(k, b)

        self.qubits = {complex(q): self.qubits[q] for q in sorted_complex(self.qubits.keys())}
        self._hash: int = hash(tuple(self.qubits.items()))

    @property
    def pauli_string(self) -> 'PauliString':
        """Duck-typing compatibility with KeyedPauliString."""
        return self

    def keyed(self, key: int) -> 'KeyedPauliString':
        from gen._core import KeyedPauliString
        return KeyedPauliString(key=key, pauli_string=self)

    def _mul_term(self, q: complex, b: Literal["X", "Y", "Z"]):
        new_b = _multiplication_table[self.qubits.pop(q, None)][b]
        if new_b is not None:
            self.qubits[q] = new_b

    @staticmethod
    def from_stim_pauli_string(stim_pauli_string: stim.PauliString) -> "PauliString":
        return PauliString(
            {
                q: "_XYZ"[stim_pauli_string[q]]
                for q in range(len(stim_pauli_string))
                if stim_pauli_string[q]
            }
        )

    @staticmethod
    def from_tile_data(tile: "gen.Tile") -> "PauliString":
        return PauliString(
            {
                k: v
                for k, v in zip(tile.ordered_data_qubits, tile.bases)
                if k is not None
            }
        )

    def with_basis(self, basis: Literal['X', 'Y', 'Z']) -> 'PauliString':
        return PauliString({q: basis for q in self.qubits.keys()})

    def __bool__(self) -> bool:
        return bool(self.qubits)

    def __mul__(self, other: "PauliString") -> "PauliString":
        result: dict[complex, Literal["X", "Y", "Z"]] = {}
        for q in self.qubits.keys() | other.qubits.keys():
            a = self.qubits.get(q, "I")
            b = other.qubits.get(q, "I")
            ax = a in "XY"
            az = a in "YZ"
            bx = b in "XY"
            bz = b in "YZ"
            cx = ax ^ bx
            cz = az ^ bz
            c = "IXZY"[cx + cz * 2]
            if c != "I":
                result[q] = cast(Literal["X", "Y", "Z"], c)
        return PauliString(result)

    def __repr__(self) -> str:
        s = {q: self.qubits[q] for q in sorted_complex(self.qubits)}
        return f"gen.PauliString({s!r})"

    def __str__(self) -> str:
        return "*".join(
            f"{self.qubits[q]}{q}" for q in sorted_complex(self.qubits.keys())
        )

    def with_xz_flipped(self) -> "PauliString":
        remap = {'X': 'Z', 'Y': 'Y', 'Z': 'X'}
        return PauliString({
            q: remap[p]
            for q, p in self.qubits.items()
        })

    def with_xy_flipped(self) -> "PauliString":
        remap = {'X': 'Y', 'Y': 'X', 'Z': 'Z'}
        return PauliString({
            q: remap[p]
            for q, p in self.qubits.items()
        })

    def commutes(self, other: "PauliString") -> bool:
        return not self.anticommutes(other)

    def anticommutes(self, other: "PauliString") -> bool:
        t = 0
        for q in self.qubits.keys() & other.qubits.keys():
            t += self.qubits[q] != other.qubits[q]
        return t % 2 == 1

    def with_transformed_coords(
        self, transform: Callable[[complex], complex]
    ) -> "PauliString":
        return PauliString({transform(q): p for q, p in self.qubits.items()})

    def to_tile(self) -> "gen.Tile":
        from gen._core._tile import Tile

        qs = list(self.qubits.keys())
        m = qs[0] if qs else 0
        return Tile(
            bases="".join(self.qubits.values()),
            ordered_data_qubits=qs,
            measurement_qubit=m,
        )

    def __hash__(self) -> int:
        return self._hash

    def __eq__(self, other) -> bool:
        if not isinstance(other, PauliString):
            return NotImplemented
        return self.qubits == other.qubits

    def _sort_key(self) -> Any:
        return tuple((q.real, q.imag, p) for q, p in self.qubits.items())

    def __lt__(self, other) -> bool:
        if not isinstance(other, PauliString):
            return NotImplemented
        return self._sort_key() < other._sort_key()
