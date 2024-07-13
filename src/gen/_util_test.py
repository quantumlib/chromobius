import stim

from gen._util import estimate_qubit_count_during_postselection, xor_sorted


def test_xor_sorted():
    assert xor_sorted([]) == []
    assert xor_sorted([2]) == [2]
    assert xor_sorted([2, 3]) == [2, 3]
    assert xor_sorted([3, 2]) == [2, 3]
    assert xor_sorted([2, 2]) == []
    assert xor_sorted([2, 2, 2]) == [2]
    assert xor_sorted([2, 2, 2, 2]) == []
    assert xor_sorted([2, 2, 3]) == [3]
    assert xor_sorted([3, 2, 2]) == [3]
    assert xor_sorted([2, 3, 2]) == [3]
    assert xor_sorted([2, 3, 3]) == [2]
    assert xor_sorted([2, 3, 5, 7, 11, 13, 5]) == [2, 3, 7, 11, 13]


def test_estimate_qubit_count_during_postselection():
    assert (
        estimate_qubit_count_during_postselection(
            stim.Circuit(
                """
        QUBIT_COORDS(0, 0) 100
        H 55
        M 55
    """
            )
        )
        == 0
    )

    assert (
        estimate_qubit_count_during_postselection(
            stim.Circuit(
                """
        QUBIT_COORDS(0, 0) 100
        H 55
        M 55
        DETECTOR(0, 0, 0, 999) rec[-1]
    """
            )
        )
        == 1
    )

    assert (
        estimate_qubit_count_during_postselection(
            stim.Circuit(
                """
        QUBIT_COORDS(0, 0) 100
        H 55 56
        M 55
        DETECTOR(0, 0, 0, 999) rec[-1]
    """
            )
        )
        == 2
    )

    assert (
        estimate_qubit_count_during_postselection(
            stim.Circuit(
                """
        QUBIT_COORDS(0, 0) 100
        H 55 56
        M 55
        DETECTOR(0, 0, 0, 999) rec[-1]
        H 57
    """
            )
        )
        == 2
    )

    assert (
        estimate_qubit_count_during_postselection(
            stim.Circuit(
                """
        QUBIT_COORDS(0, 0) 100
        H 55 56
        M 55
        REPEAT 10 {
            H 58
        }
        DETECTOR(0, 0, 0, 999) rec[-1]
        H 57
    """
            )
        )
        == 3
    )
