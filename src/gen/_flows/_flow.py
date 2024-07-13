from typing import Iterable, Any, Optional, Callable, Literal

from gen._util import xor_sorted
from gen._core import PauliString, KeyedPauliString


class Flow:
    """A rule for how a stabilizer travels into, through, and/or out of a chunk."""

    def __init__(
        self,
        *,
        start: PauliString | None = None,
        end: PauliString | None = None,
        measurement_indices: Iterable[int] | Literal['auto'] = (),
        obs_index: Any = None,
        center: complex,
        flags: Iterable[str] = frozenset(),
    ):
        self.start = PauliString({}) if start is None else start
        self.end = PauliString({}) if end is None else end
        self.measurement_indices: tuple[int, ...] | Literal['auto'] = measurement_indices if measurement_indices == 'auto' else tuple(xor_sorted(measurement_indices))
        self.flags = frozenset(flags)
        self.obs_index = obs_index
        self.center = center
        if measurement_indices == 'auto' and not start and not end:
            raise ValueError("measurement_indices == 'auto' and not start and not end")

    @property
    def key_start(self) -> KeyedPauliString | PauliString:
        if self.obs_index is None:
            return self.start
        return self.start.keyed(self.obs_index)

    @property
    def key_end(self) -> KeyedPauliString | PauliString:
        if self.obs_index is None:
            return self.end
        return self.end.keyed(self.obs_index)

    def with_edits(
            self,
            *,
            start: PauliString | None = None,
            end: PauliString | None = None,
            measurement_indices: Iterable[int] | None = None,
            obs_index: Any = 'not_specified',
            center: complex | None = None,
            flags: Iterable[str] | None = None,
    ) -> 'Flow':
        return Flow(
            start=self.start if start is None else start,
            end=self.end if end is None else end,
            measurement_indices=self.measurement_indices if measurement_indices is None else measurement_indices,
            obs_index=self.obs_index if obs_index == 'not_specified' else obs_index,
            center=self.center if center is None else center,
            flags=self.flags if flags is None else flags,
        )

    def __eq__(self, other):
        if not isinstance(other, Flow):
            return NotImplemented
        return (
            self.start == other.start
            and self.end == other.end
            and self.measurement_indices == other.measurement_indices
            and self.obs_index == other.obs_index
            and self.flags == other.flags
            and self.center == other.center
        )

    def __str__(self):
        start_terms = []
        for q, p in self.start.qubits.items():
            start_terms.append(f'{p}[{q}]')
        end_terms = []
        for q, p in self.end.qubits.items():
            q = complex(q)
            if q.real == 0:
                q = '0+' + str(q)
            q = str(q).replace('(', '').replace(')', '')
            end_terms.append(f'{p}[{q}]')
        if self.measurement_indices == 'auto':
            end_terms.append('rec[auto]')
        else:
            for m in self.measurement_indices:
                end_terms.append(f'rec[{m}]')
        if not start_terms:
            start_terms.append('1')
        if not end_terms:
            end_terms.append('1')
        key = '' if self.obs_index is None else f' (obs={self.obs_index})'
        return f'{"*".join(start_terms)} -> {"*".join(end_terms)}{key}'

    def __repr__(self):
        return (
            f"Flow(start={self.start!r}, "
            f"end={self.end!r}, "
            f"measurement_indices={self.measurement_indices!r}, "
            f"flags={sorted(self.flags)}, "
            f"obs_index={self.obs_index!r}, "
            f"center={self.center!r}"
        )

    def postselected(self) -> "Flow":
        return Flow(
            start=self.start,
            end=self.end,
            measurement_indices=self.measurement_indices,
            obs_index=self.obs_index,
            flags=self.flags | {"postselect"},
            center=self.center,
        )

    def with_xz_flipped(self) -> "Flow":
        return Flow(
            start=self.start.with_xz_flipped(),
            end=self.end.with_xz_flipped(),
            measurement_indices=self.measurement_indices,
            obs_index=self.obs_index,
            flags=self.flags,
            center=self.center,
        )

    def with_transformed_coords(
        self, transform: Callable[[complex], complex]
    ) -> "Flow":
        return Flow(
            start=self.start.with_transformed_coords(transform),
            end=self.end.with_transformed_coords(transform),
            measurement_indices=self.measurement_indices,
            obs_index=self.obs_index,
            flags=self.flags,
            center=transform(self.center),
        )

    def concat(self, other: "Flow", other_measure_offset: int) -> "Flow":
        if other.start != self.end:
            raise ValueError("other.start != self.end")
        if other.obs_index != self.obs_index:
            raise ValueError("other.obs_index != self.obs_index")
        return Flow(
            start=self.start,
            end=other.end,
            center=(self.center + other.center) / 2,
            measurement_indices=self.measurement_indices + tuple(m + other_measure_offset for m in other.measurement_indices),
            obs_index=self.obs_index,
            flags=self.flags | other.flags,
        )

    def __mul__(self, other: 'Flow') -> 'Flow':
        if other.obs_index != self.obs_index:
            raise ValueError("other.obs_index != self.obs_index")
        return Flow(
            start=self.start * other.start,
            end=self.end * other.end,
            measurement_indices=sorted(set(self.measurement_indices) ^ set(other.measurement_indices)),
            obs_index=self.obs_index,
            flags=self.flags | other.flags,
            center=(self.center + other.center) / 2,
        )
