import dataclasses
from typing import Iterable, Any

import stim


@dataclasses.dataclass(frozen=True)
class AtLayer:
    """A special class that indicates the layer to read a measurement key from."""

    key: Any
    layer: Any


class MeasurementTracker:
    """Tracks measurements and groups of measurements, for producing stim record targets."""

    def __init__(self):
        self.recorded: dict[Any, list[int] | None] = {}
        self.next_measurement_index = 0

    def copy(self) -> "MeasurementTracker":
        result = MeasurementTracker()
        result.recorded = {k: list(v) for k, v in self.recorded.items()}
        result.next_measurement_index = self.next_measurement_index
        return result

    def _rec(self, key: Any, value: list[int] | None) -> None:
        if key in self.recorded:
            raise ValueError(f"Measurement key collision: {key=}")
        self.recorded[key] = value

    def record_measurement(self, key: Any) -> None:
        self._rec(key, [self.next_measurement_index])
        self.next_measurement_index += 1

    def make_measurement_group(self, sub_keys: Iterable[Any], *, key: Any) -> None:
        self._rec(key, self.lookup_recs(sub_keys))

    def record_obstacle(self, key: Any) -> None:
        self._rec(key, None)

    def lookup_recs(self, keys: Iterable[Any]) -> list[int] | None:
        result = set()
        for key in keys:
            if key not in self.recorded:
                raise ValueError(f"No such measurement: {key=}")
            r = self.recorded[key]
            if r is None:
                return None
            for v in r:
                if v is None:
                    raise ValueError(f"Obstacle at {key=}")
                if v in result:
                    result.remove(v)
                else:
                    result.add(v)
        return sorted(result)

    def current_measurement_record_targets_for(
        self, keys: Iterable[Any]
    ) -> list[stim.GateTarget] | None:
        t0 = self.next_measurement_index
        times = self.lookup_recs(keys)
        if times is None:
            return None
        return [stim.target_rec(t - t0) for t in sorted(times)]
