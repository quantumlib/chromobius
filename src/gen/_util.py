import io
import pathlib
from typing import Callable, Any, TypeVar, Iterable

import stim


def stim_circuit_with_transformed_coords(
    circuit: stim.Circuit, transform: Callable[[complex], complex]
) -> stim.Circuit:
    """Returns an equivalent circuit, but with the qubit and detector position metadata modified.
    The "position" is assumed to be the first two coordinates. These are mapped to the real and
    imaginary values of a complex number which is then transformed.

    Note that `SHIFT_COORDS` instructions that modify the first two coordinates are not supported.
    This is because supporting them requires flattening loops, or promising that the given
    transformation is affine.

    Args:
        circuit: The circuit with qubits to reposition.
        transform: The transformation to apply to the positions. The positions are given one by one
            to this method, as complex numbers. The method returns the new complex number for the
            position.

    Returns:
        The transformed circuit.
    """
    result = stim.Circuit()
    for instruction in circuit:
        if isinstance(instruction, stim.CircuitInstruction):
            if instruction.name == "QUBIT_COORDS" or instruction.name == "DETECTOR":
                args = list(instruction.gate_args_copy())
                while len(args) < 2:
                    args.append(0)
                c = transform(args[0] + args[1] * 1j)
                args[0] = c.real
                args[1] = c.imag
                result.append(instruction.name, instruction.targets_copy(), args)
                continue
            if instruction.name == "SHIFT_COORDS":
                args = instruction.gate_args_copy()
                if any(args[:2]):
                    raise NotImplementedError(
                        f"Shifting first two coords: {instruction=}"
                    )

        if isinstance(instruction, stim.CircuitRepeatBlock):
            result.append(
                stim.CircuitRepeatBlock(
                    repeat_count=instruction.repeat_count,
                    body=stim_circuit_with_transformed_coords(
                        instruction.body_copy(), transform
                    ),
                )
            )
            continue

        result.append(instruction)
    return result


def stim_circuit_with_transformed_moments(
    circuit: stim.Circuit, *, moment_func: Callable[[stim.Circuit], stim.Circuit]
) -> stim.Circuit:
    """Applies a transformation to regions of a circuit separated by TICKs and blocks.

    For example, in this circuit:

        H 0
        X 0
        TICK

        H 1
        X 1
        REPEAT 100 {
            H 2
            X 2
        }
        H 3
        X 3

        TICK
        H 4
        X 4

    `moment_func` would be called five times, each time with one of the H and X instruction pairs.
    The result from the method would then be substituted into the circuit, replacing each of the H
    and X instruction pairs.

    Args:
        circuit: The circuit to return a transformed result of.
        moment_func: The transformation to apply to regions of the circuit. Returns a new circuit
            for the result.

    Returns:
        A transformed circuit.
    """

    result = stim.Circuit()
    current_moment = stim.Circuit()

    for instruction in circuit:
        if isinstance(instruction, stim.CircuitRepeatBlock):
            # Implicit tick at transition into REPEAT?
            if current_moment:
                result += moment_func(current_moment)
                current_moment.clear()

            transformed_body = stim_circuit_with_transformed_moments(
                instruction.body_copy(), moment_func=moment_func
            )
            result.append(
                stim.CircuitRepeatBlock(
                    repeat_count=instruction.repeat_count, body=transformed_body
                )
            )
        elif (
            isinstance(instruction, stim.CircuitInstruction)
            and instruction.name == "TICK"
        ):
            # Explicit tick. Process even if empty.
            result += moment_func(current_moment)
            result.append("TICK")
            current_moment.clear()
        else:
            current_moment.append(instruction)

    # Implicit tick at end of circuit?
    if current_moment:
        result += moment_func(current_moment)

    return result


def estimate_qubit_count_during_postselection(circuit: stim.Circuit) -> int:
    circuit = circuit.without_noise()
    start = 0
    end = 0
    for k, instruction in enumerate(circuit):
        if isinstance(instruction, stim.CircuitInstruction):
            if instruction.name == "QUBIT_COORDS":
                start = k + 1
            elif instruction.name == "DETECTOR":
                args = instruction.gate_args_copy()
                if len(args) >= 4 and args[3] == 999:
                    end = k + 1
    used_qubits = set()

    def process(sub_circuit: stim.Circuit):
        for inst in sub_circuit:
            if isinstance(inst, stim.CircuitRepeatBlock):
                process(inst.body_copy())
            else:
                for t in inst.targets_copy():
                    if t.is_qubit_target:
                        used_qubits.add(t.value)

    process(circuit[start:end])
    return len(used_qubits)


def write_file(path: str | pathlib.Path | io.IOBase, content: Any):
    if isinstance(path, io.IOBase):
        path.write(content)
        return
    elif isinstance(content, bytes):
        with open(path, "wb") as f:
            print(content, file=f)
    else:
        with open(path, "w") as f:
            print(content, file=f)
    print(f"wrote file://{pathlib.Path(path).absolute()}")


TItem = TypeVar('TItem')


def xor_sorted(vals: Iterable[TItem], *, key: Callable[[TItem], Any] = lambda e: e) -> list[TItem]:
    """Sorts items and then cancels pairs of equal items.

    An item will be in the result once if it appeared an odd number of times.
    An item won't be in the result if it appeared an even number of times.
    """
    result = sorted(vals, key=key)
    n = len(result)
    skipped = 0
    k = 0
    while k + 1 < n:
        if result[k] == result[k + 1]:
            skipped += 2
            k += 2
        else:
            result[k - skipped] = result[k]
            k += 1
    if k < n:
        result[k - skipped] = result[k]
    while skipped:
        result.pop()
        skipped -= 1
    return result
