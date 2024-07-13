from gen._core._pauli_string import PauliString


def test_mul():
    a = "IIIIXXXXYYYYZZZZ"
    b = "IXYZ" * 4
    c = "IXYZXIZYYZIXZYXI"
    a = PauliString({q: p for q, p in enumerate(a) if p != "I"})
    b = PauliString({q: p for q, p in enumerate(b) if p != "I"})
    c = PauliString({q: p for q, p in enumerate(c) if p != "I"})
    assert a * b == c
