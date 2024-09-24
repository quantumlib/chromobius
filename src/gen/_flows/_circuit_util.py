import stim

XZ_FLIPPED = {
    "I": "I",
    "X": "Z",
    "Y": "Y",
    "Z": "X",
    "C_XYZ": "C_ZYX",
    "C_ZYX": "C_XYZ",
    "H": "H",
    "H_XY": "H_YZ",
    "H_XZ": "H_XZ",
    "H_YZ": "H_XY",
    "S": "SQRT_X",
    "SQRT_X": "S",
    "SQRT_X_DAG": "S_DAG",
    "SQRT_Y": "SQRT_Y",
    "SQRT_Y_DAG": "SQRT_Y_DAG",
    "S_DAG": "SQRT_X_DAG",
    "CX": "XCZ",
    "CY": "XCY",
    "CZ": "XCX",
    "ISWAP": None,
    "ISWAP_DAG": None,
    "SQRT_XX": "SQRT_ZZ",
    "SQRT_XX_DAG": "SQRT_ZZ_DAG",
    "SQRT_YY": "SQRT_YY",
    "SQRT_YY_DAG": "SQRT_YY_DAG",
    "SQRT_ZZ": "SQRT_XX",
    "SQRT_ZZ_DAG": "SQRT_XX_DAG",
    "SWAP": "SWAP",
    "XCX": "CZ",
    "XCY": "CY",
    "XCZ": "CX",
    "YCX": "YCZ",
    "YCY": "YCY",
    "YCZ": "YCX",
    "DEPOLARIZE1": "DEPOLARIZE1",
    "DEPOLARIZE2": "DEPOLARIZE2",
    "E": None,
    "ELSE_CORRELATED_ERROR": None,
    "PAULI_CHANNEL_1": None,
    "PAULI_CHANNEL_2": None,
    "X_ERROR": "Z_ERROR",
    "Y_ERROR": "Y_ERROR",
    "Z_ERROR": "X_ERROR",
    "M": "MX",
    "MPP": None,
    "MR": "MRX",
    "MRX": "MRZ",
    "MRY": "MRY",
    "MX": "M",
    "MY": "MY",
    "R": "RX",
    "RX": "R",
    "RY": "RY",
    "DETECTOR": "DETECTOR",
    "OBSERVABLE_INCLUDE": "OBSERVABLE_INCLUDE",
    "QUBIT_COORDS": "QUBIT_COORDS",
    "SHIFT_COORDS": "SHIFT_COORDS",
    "TICK": "TICK",
}


def circuit_with_xz_flipped(circuit: stim.Circuit) -> stim.Circuit:
    result = stim.Circuit()
    for inst in circuit:
        if isinstance(inst, stim.CircuitRepeatBlock):
            result.append(
                stim.CircuitRepeatBlock(
                    body=circuit_with_xz_flipped(inst.body_copy()),
                    repeat_count=inst.repeat_count,
                )
            )
        else:
            other = XZ_FLIPPED.get(inst.name)
            if other is None:
                raise NotImplementedError(f"{inst=}")
            result.append(
                stim.CircuitInstruction(
                    other, inst.targets_copy(), inst.gate_args_copy()
                )
            )
    return result


def circuit_to_dem_target_measurement_records_map(circuit: stim.Circuit) -> dict[stim.DemTarget, list[int]]:
    result = {}
    for k in range(circuit.num_observables):
        result[stim.target_logical_observable_id(k)] = []
    num_d = 0
    num_m = 0
    for inst in circuit.flattened():
        if inst.name == 'DETECTOR':
            result[stim.target_relative_detector_id(num_d)] = [num_m + t.value for t in inst.targets_copy()]
            num_d += 1
        elif inst.name == 'OBSERVABLE_INCLUDE':
            result[stim.target_logical_observable_id(int(inst.gate_args_copy()[0]))].extend(num_m + t.value for t in inst.targets_copy())
        else:
            c = stim.Circuit()
            c.append(inst)
            num_m += c.num_measurements
    return result
