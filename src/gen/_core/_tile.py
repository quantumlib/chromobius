import functools
from typing import Iterable, Callable, Literal, TYPE_CHECKING
from typing import cast

if TYPE_CHECKING:
    import gen


class Tile:
    """A stabilizer with additional information related to how it is measured.

    Annotates the order in which data qubits are touched, the relevant basis of
    each data qubit, and also the measurement ancilla.
    """

    def __init__(
        self,
        *,
        bases: str,
        measurement_qubit: complex,
        ordered_data_qubits: Iterable[complex | None],
        flags: Iterable[str] = (),
    ):
        """
        Args:
            bases: Basis of the stabilizer. A string of XYZ characters the same
                length as the ordered_data_qubits argument. It is permitted to
                give a single-character string, which will automatically be
                expanded to the full length. For example, "X" will become "XXXX"
                if there are four data qubits.
            measurement_qubit: The ancilla qubit used to measure the stabilizer.
            ordered_data_qubits: The data qubits in the stabilizer, in the order
                that they are interacted with. Some entries may be None,
                indicating that no data qubit is interacted with during the
                corresponding interaction layer.
        """
        assert isinstance(bases, str)
        self.ordered_data_qubits = tuple(ordered_data_qubits)
        self.measurement_qubit = measurement_qubit
        if len(bases) == 1:
            bases *= len(self.ordered_data_qubits)
        self.bases: str = bases
        self.flags: frozenset[str] = frozenset(flags)
        if len(self.bases) != len(self.ordered_data_qubits):
            raise ValueError("len(self.bases_2) != len(self.data_qubits_order)")

    def to_data_pauli_string(self) -> "gen.PauliString":
        from gen._core._pauli_string import PauliString

        return PauliString(
            {
                q: b
                for q, b in zip(self.ordered_data_qubits, self.bases)
                if q is not None
            }
        )

    def with_data_qubit_cleared(self, q: complex) -> "Tile":
        return self.with_edits(ordered_data_qubits=[
            None if d == q else d for d in self.ordered_data_qubits
        ])

    def with_edits(
            self,
            *,
            bases: str | None = None,
            measurement_qubit: complex | None = None,
            ordered_data_qubits: Iterable[complex] | None = None,
            extra_coords: Iterable[float] | None = None,
            flags: Iterable[str] = None,
    ) -> 'Tile':
        if ordered_data_qubits is not None:
            ordered_data_qubits = tuple(ordered_data_qubits)
            if len(ordered_data_qubits) != len(self.ordered_data_qubits) and bases is None:
                if self.basis is None:
                    raise ValueError("Changed data qubit count of non-uniform basis tile.")
                bases = self.basis

        return Tile(
            bases=self.bases if bases is None else bases,
            measurement_qubit=self.measurement_qubit if measurement_qubit is None else measurement_qubit,
            ordered_data_qubits=self.ordered_data_qubits if ordered_data_qubits is None else ordered_data_qubits,
            flags=self.flags if flags is None else flags,
        )

    def with_bases(self, bases: str) -> "Tile":
        return self.with_edits(bases=bases)
    with_basis = with_bases

    def with_xz_flipped(self) -> "Tile":
        f = {"X": "Z", "Y": "Y", "Z": "X"}
        return self.with_bases("".join(f[e] for e in self.bases))

    def __eq__(self, other):
        if not isinstance(other, Tile):
            return False
        return (
            self.ordered_data_qubits == other.ordered_data_qubits
            and self.measurement_qubit == other.measurement_qubit
            and self.bases == other.bases
        )

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash(
            (
                Tile,
                self.ordered_data_qubits,
                self.measurement_qubit,
                self.bases,
                self.flags,
            )
        )

    def __repr__(self):
        b = self.basis or self.bases
        extra = (
            ""
            if not self.flags
            else f"\n    flags={sorted(self.flags)!r},"
        )
        return f"""gen.Tile(
    ordered_data_qubits={self.ordered_data_qubits!r},
    measurement_qubit={self.measurement_qubit!r},
    bases={b!r},{extra}
)"""

    def with_transformed_coords(
        self, coord_transform: Callable[[complex], complex]
    ) -> "Tile":
        return self.with_edits(
            ordered_data_qubits=[
                None if d is None else coord_transform(d)
                for d in self.ordered_data_qubits
            ],
            measurement_qubit=coord_transform(self.measurement_qubit),
        )

    def after_basis_transform(
        self,
        basis_transform: Callable[[Literal["X", "Y", "Z"]], Literal["X", "Y", "Z"]],
    ) -> "Tile":
        return self.with_bases("".join(
            basis_transform(cast(Literal["X", "Y", "Z"], e)) for e in self.bases
        ))

    @functools.cached_property
    def data_set(self) -> frozenset[complex]:
        return frozenset(e for e in self.ordered_data_qubits if e is not None)

    @functools.cached_property
    def used_set(self) -> frozenset[complex]:
        return self.data_set | frozenset([self.measurement_qubit])

    @functools.cached_property
    def basis(self) -> Literal["X", "Y", "Z"] | None:
        bs = {b for q, b in zip(self.ordered_data_qubits, self.bases) if q is not None}
        if len(bs) == 0:
            # Fallback to including ejected qubits.
            bs = set(self.bases)
        if len(bs) != 1:
            return None
        return next(iter(bs))
