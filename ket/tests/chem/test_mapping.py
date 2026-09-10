"""Unit tests for mappings in ket."""
# pylint: disable=invalid-name

# SPDX-FileCopyrightText: 2026 Maria Eduarda W. M. Vianna <maria.vianna@grad.ufsc.br>
# SPDX-FileCopyrightText: 2026 Erico Souza Teixeira <erico.teixeira@venturus.org.br>
#
# SPDX-License-Identifier: Apache-2.0

"""Unit testing for fermion-to-qubit mappings."""

import pytest
import cmath
from ket import Process
from ket.chem import (
    Fermion,
    FermionSentence,
    jordan_wigner,
    bravyi_kitaev,
    symmetry_conserving_bravyi_kitaev,
)


def test_jordan_wigner_creation_operator():
    """Test Jordan-Wigner for a single creation operator: a^†_0 -> (X0 - iY0)/2."""
    p = Process()
    q = p.alloc(1)

    op = Fermion({(0, 0, "a"): "+"})
    h = jordan_wigner(op, q)

    assert len(h.terms) == 2

    x_term = next(t for t in h.terms if t.map.get(q.qubits[0]) == "X")
    y_term = next(t for t in h.terms if t.map.get(q.qubits[0]) == "Y")

    assert cmath.isclose(x_term.coef, 0.5)
    assert cmath.isclose(y_term.coef, -0.5j)


def test_jordan_wigner_annihilation_operator():
    """Test Jordan-Wigner for a single annihilation operator: a_0 -> (X0 + iY0)/2."""
    p = Process()
    q = p.alloc(1)

    op = Fermion({(0, 0, "a"): "-"})
    h = jordan_wigner(op, q)

    assert len(h.terms) == 2

    x_term = next(t for t in h.terms if t.map.get(q.qubits[0]) == "X")
    y_term = next(t for t in h.terms if t.map.get(q.qubits[0]) == "Y")

    assert cmath.isclose(x_term.coef, 0.5)
    assert cmath.isclose(y_term.coef, 0.5j)


def test_jordan_wigner_number_operator_term():
    """Test Jordan-Wigner for a number operator term: 0^ 0 -> 0.5*I - 0.5*Z0."""
    p = Process()
    q = p.alloc(1)

    op = Fermion({(0, 0, "a"): "+", (1, 0, "a"): "-"})
    h = jordan_wigner(op, q)

    assert len(h.terms) == 2

    identity_term = next(t for t in h.terms if not any(op in "XYZ" for op in t.map.values()))
    z_term = next(t for t in h.terms if t.map.get(q.qubits[0]) == "Z")

    assert cmath.isclose(identity_term.coef, 0.5)
    assert cmath.isclose(z_term.coef, -0.5)


def test_jordan_wigner_fermion_sentence():
    """Test Jordan-Wigner mapping for a linear combination: 2(a^†_0 a_0) - (a^†_1 a_1) -> 
    0.5*I - 1.0*Z0 + 0.5*Z1"""
    p = Process()
    q = p.alloc(2)

    term1 = Fermion({(0, 0, "a"): "+", (1, 0, "a"): "-"})
    term2 = Fermion({(0, 1, "a"): "+", (1, 1, "a"): "-"})
    fs = FermionSentence({term1: 2.0, term2: -1.0})

    h = jordan_wigner(fs, q)

    assert len(h.terms) == 3

    identity_term = next(t for t in h.terms if not any(op in "XYZ" for op in t.map.values()))
    z0_term = next(t for t in h.terms if t.map.get(q.qubits[0]) == "Z" and t.map.get(q.qubits[1], "I") == "I")
    z1_term = next(t for t in h.terms if t.map.get(q.qubits[1]) == "Z" and t.map.get(q.qubits[0], "I") == "I")

    assert cmath.isclose(identity_term.coef, 0.5)
    assert cmath.isclose(z0_term.coef, -1.0)
    assert cmath.isclose(z1_term.coef, 0.5)


def test_jordan_wigner_hopping_term():
    """Test Jordan-Wigner mapping for a hopping term: a^†_0 a_1."""
    p = Process()
    q = p.alloc(2)

    op = Fermion({(0, 0, "a"): "+", (1, 1, "a"): "-"})
    h = jordan_wigner(op, q)

    assert len(h.terms) == 4

    for term in h.terms:
        m0 = term.map.get(q.qubits[0])
        m1 = term.map.get(q.qubits[1])

        if m0 == "X" and m1 == "X":
            assert cmath.isclose(term.coef, 0.25)
        elif m0 == "Y" and m1 == "Y":
            assert cmath.isclose(term.coef, 0.25)
        elif m0 == "X" and m1 == "Y":
            assert cmath.isclose(term.coef, 0.25j)
        elif m0 == "Y" and m1 == "X":
            assert cmath.isclose(term.coef, -0.25j)
        else:
            pytest.fail(f"Unexpected Pauli term: {term}")


def test_jordan_wigner_empty_fermion():
    """Test Jordan-Wigner for an empty Fermion product (Identity)."""
    p = Process()
    q = p.alloc(1)

    op = Fermion({})
    h = jordan_wigner(op, q)

    assert len(h.terms) == 1
    assert len(h.terms[0].map) == 0
    assert cmath.isclose(h.terms[0].coef, 1.0)


def test_jordan_wigner_invalid_type():
    """Test that jordan_wigner raises TypeError for unsupported input types."""
    p = Process()
    q = p.alloc(1)

    with pytest.raises(TypeError, match="operator must be Fermion or FermionSentence"):
        jordan_wigner("invalid_type", q)

def test_jordan_wigner_creation_with_z_string():
    """Test Jordan-Wigner Z-string for higher orbitals: a^†_3 -> Z_0 Z_1 Z_2 (X_3 - iY_3)/2."""
    p = Process()
    q = p.alloc(4)

    op = Fermion({(0, 3, "a"): "+"})
    h = jordan_wigner(op, q)

    assert len(h.terms) == 2

    for term in h.terms:
        assert term.map[q.qubits[0]] == "Z"
        assert term.map[q.qubits[1]] == "Z"
        assert term.map[q.qubits[2]] == "Z"

def test_jordan_wigner_orbital_out_of_range():
    """Test ValueError is raised when the orbital index exceeds the number of allocated qubits."""
    p = Process()
    q = p.alloc(1)

    op = Fermion({(0, 3, "a"): "+"})

    with pytest.raises(ValueError):
        jordan_wigner(op, q)

def test_jordan_wigner_null_operator():
    """Test Jordan-Wigner maps physically impossible states to the null operator: a^†_1 a^†_1 a_1 a_1 -> 0."""
    p = Process()
    q = p.alloc(2)

    op = Fermion({(0, 1, "a"): "+", (1, 1, "a"): "+", (2, 1, "a"): "-", (3, 1, "a"): "-"})
    h = jordan_wigner(op, q)

    assert len(h.terms) == 0 


def test_jordan_wigner_annihilation_then_creation():
    """Test Jordan-Wigner for inverted order: a_0 a^†_0 -> 0.5*I + 0.5*Z0."""
    p = Process()
    q = p.alloc(1)

    op = Fermion({(0, 0, "a"): "-", (1, 0, "a"): "+"})
    h = jordan_wigner(op, q)

    assert len(h.terms) == 2

    identity_term = next(t for t in h.terms if not any(op in "XYZ" for op in t.map.values()))
    z_term = next(t for t in h.terms if t.map.get(q.qubits[0]) == "Z")

    assert cmath.isclose(identity_term.coef, 0.5)
    assert cmath.isclose(z_term.coef, 0.5)  

def test_scbk_invalid_qubit_length():
    """Test that SCBK raises ValueError if active_orbitals doesn't match qubit register."""
    p = Process()
    q = p.alloc(2) 

    op = Fermion({(0, 0, "a"): "+", (1, 0, "a"): "-"})

    with pytest.raises(ValueError, match="active_orbitals must match the length of the qubits register."):
        symmetry_conserving_bravyi_kitaev(op, q, active_orbitals=4, n_alpha=1, n_beta=1)


def test_scbk_qubit_removal():
    """Test if SCBK correctly drops the middle and final parity qubits for N=4."""
    p = Process()
    q = p.alloc(4)

    # Creating a hopping term to generate a complex mix of X, Y, Z in standard BK
    op = FermionSentence({
        Fermion({(0, 0, "a"): "+", (1, 1, "a"): "-"}): 1.0,
        Fermion({(0, 2, "a"): "+", (1, 3, "a"): "-"}): 1.0
    })
    
    # 4 orbitals, 2 active fermions (Parity: middle=-1, final=1)
    h = symmetry_conserving_bravyi_kitaev(op, q, active_orbitals=4, n_alpha=1, n_beta=1)
    
    # In a 4-qubit system, the targets are index 1 (middle) and 3 (final)
    target_middle_id = q.qubits[1]
    target_final_id = q.qubits[3]

    for term in h.terms:
        # The removed qubits should no longer exist in any Pauli map, meaning
        # all remaining qubit indices must be less than active_orbitals - 2
        assert all(q_idx < 4 - 2 for q_idx in term.map)


def test_scbk_term_survival():
    """Test that parity injection and symmetry dropping leaves a valid Hamiltonian."""
    p = Process()
    q = p.alloc(4)

    # Number operator on orbital 0
    op = Fermion({(0, 0, "a"): "+", (1, 0, "a"): "-"})
    
    h = symmetry_conserving_bravyi_kitaev(op, q, active_orbitals=4, n_alpha=1, n_beta=1)
    
    # Even after reducing 2 qubits, the resulting Hamiltonian must not be empty
    assert len(h.terms) > 0
    
    # Ensure no term was left with a coefficient of exactly zero (should be filtered)
    for term in h.terms:
        assert abs(term.coef) > 1e-10


def test_scbk_n6_qubit_removal():
    """Test if SCBK correctly drops the middle and final parity qubits for N=6."""
    p = Process()
    q = p.alloc(6)

    # CORRECTED: Using physically valid hopping terms that conserve spin
    # 0 -> 2 (alpha to alpha)
    # 1 -> 3 (beta to beta)
    op = FermionSentence({
        Fermion({(0, 0, "a"): "+", (1, 2, "a"): "-"}): 1.0,
        Fermion({(0, 1, "a"): "+", (1, 3, "a"): "-"}): 1.0
    })
    
    # 6 orbitals, 4 active fermions (Parity: middle=1, final=1)
    h = symmetry_conserving_bravyi_kitaev(op, q, active_orbitals=6, n_alpha=2, n_beta=2)
    
    # In a 6-qubit system, the targets are index 2 (middle) and 5 (final)
    target_middle_id = q.qubits[2]
    target_final_id = q.qubits[5]

    for term in h.terms:
        # The removed qubits should no longer exist in any Pauli map, meaning
        # all remaining qubit indices must be less than active_orbitals - 2
        assert all(q_idx < 6 - 2 for q_idx in term.map)

    # Ensure the Hamiltonian isn't zeroed out
    assert len(h.terms) > 0


def test_scbk_spin_polarised():
    """Test SCBK with arbitrary spin configurations, checking exact coefficients and signs."""
    p = Process()
    q = p.alloc(4)

    # Number operator on orbital 2 (which is alpha spin, mapping to position 1)
    # In BK-Tree, n'_1 maps to 0.5 * (I - Z_1 * Z_0).
    # Since qubit 1 (middle) is removed, Z_1 is replaced by parity_alpha.
    # The resulting Hamiltonian should be: 0.5 * I - 0.5 * parity_alpha * Z_0.
    op = Fermion({(0, 2, "a"): "+", (1, 2, "a"): "-"})
    
    # 1. Singlet case: 1 alpha, 1 beta
    # parity_alpha = (-1)**1 = -1
    # Expected Hamiltonian: 0.5 * I + 0.5 * Z_0
    h_singlet = symmetry_conserving_bravyi_kitaev(op, q, active_orbitals=4, n_alpha=1, n_beta=1)
    
    identity_s = next(t for t in h_singlet.terms if not any(op in "XYZ" for op in t.map.values()))
    z0_s = next(t for t in h_singlet.terms if t.map.get(q.qubits[0]) == "Z")
    
    assert cmath.isclose(identity_s.coef, 0.5)
    assert cmath.isclose(z0_s.coef, 0.5)  # Sign becomes positive because parity_alpha is -1

    # 2. Polarized Triplet case: 2 alpha, 0 beta
    # parity_alpha = (-1)**2 = 1
    # Expected Hamiltonian: 0.5 * I - 0.5 * Z_0
    h_triplet = symmetry_conserving_bravyi_kitaev(op, q, active_orbitals=4, n_alpha=2, n_beta=0)
    
    identity_t = next(t for t in h_triplet.terms if not any(op in "XYZ" for op in t.map.values()))
    z0_t = next(t for t in h_triplet.terms if t.map.get(q.qubits[0]) == "Z")
    
    assert cmath.isclose(identity_t.coef, 0.5)
    assert cmath.isclose(z0_t.coef, -0.5)  # Sign stays negative because parity_alpha is 1


def test_bravyi_kitaev_tree_vs_bitwise_power_of_two():
    """Test that tree-based BK and bitwise BK yield identical results for N=4."""
    p = Process()
    q = p.alloc(4)

    # 1. Test single creation operator
    op_creation = Fermion({(0, 2, "a"): "+"})
    h_tree = bravyi_kitaev(op_creation, q, tree=True)
    h_bit = bravyi_kitaev(op_creation, q, tree=False)
    
    assert len(h_tree.terms) == len(h_bit.terms)
    
    def get_terms_dict(h):
        return {"".join(f"{p}{q}" for q, p in sorted(term.map.items())): term.coef for term in h.terms}
        
    dict_tree = get_terms_dict(h_tree)
    dict_bit = get_terms_dict(h_bit)
    
    assert dict_tree.keys() == dict_bit.keys()
    for k in dict_tree:
        assert cmath.isclose(dict_tree[k], dict_bit[k])

    # 2. Test hopping term
    op_hopping = Fermion({(0, 0, "a"): "+", (1, 1, "a"): "-"})
    h_tree = bravyi_kitaev(op_hopping, q, tree=True)
    h_bit = bravyi_kitaev(op_hopping, q, tree=False)
    
    dict_tree = get_terms_dict(h_tree)
    dict_bit = get_terms_dict(h_bit)
    
    assert dict_tree.keys() == dict_bit.keys()
    for k in dict_tree:
        assert cmath.isclose(dict_tree[k], dict_bit[k])

def test_bravyi_kitaev_non_power_of_two():
    """Test that tree-based BK works for N=3 (non-power-of-two)."""
    p = Process()
    q = p.alloc(3)

    op = Fermion({(0, 1, "a"): "+", (1, 2, "a"): "-"})
    
    # Should run successfully without raising exceptions
    h_tree = bravyi_kitaev(op, q, tree=True)
    assert len(h_tree.terms) > 0
    for term in h_tree.terms:
        # All mapped qubits must be in range of 3 qubits
        assert all(q_idx < 3 for q_idx in term.map)


def test_bravyi_kitaev_bitwise_single_operators():
    """Test bitwise Bravyi-Kitaev (tree=False) for single creation and number operators."""
    p = Process()
    q = p.alloc(4)

    # 1. Single creation operator a^†_0 -> (X0 - iY0)/2
    op0 = Fermion({(0, 0, "a"): "+"})
    h0 = bravyi_kitaev(op0, q, tree=False)
    assert len(h0.terms) == 2

    # 2. Number operator a^†_0 a_0 -> (I - Z0)/2
    op_num = Fermion({(0, 0, "a"): "+", (1, 0, "a"): "-"})
    h_num = bravyi_kitaev(op_num, q, tree=False)
    assert len(h_num.terms) == 2
    id_term = next(t for t in h_num.terms if not any(v in "XYZ" for v in t.map.values()))
    z0_term = next(t for t in h_num.terms if t.map.get(q.qubits[0]) == "Z")
    assert cmath.isclose(id_term.coef, 0.5)
    assert cmath.isclose(z0_term.coef, -0.5)


def test_bravyi_kitaev_bitwise_non_power_of_two():
    """Test bitwise Bravyi-Kitaev (tree=False) executes correctly for N=3 (non-power-of-two)."""
    p = Process()
    q = p.alloc(3)

    op = Fermion({(0, 0, "a"): "+", (1, 2, "a"): "-"})
    h_bit = bravyi_kitaev(op, q, tree=False)

    assert len(h_bit.terms) > 0
    for term in h_bit.terms:
        assert all(q_idx < 3 for q_idx in term.map)


# --------------------------------------------------------------------------
# Cross-Validation Tests: Ket Mappings vs OpenFermion
# --------------------------------------------------------------------------

def _ket_to_canonical_dict(h_ket):
    """Convert Ket qubit Hamiltonian into a canonical dict {pauli_string: coefficient}."""
    d = {}
    for term in h_ket.terms:
        clean = {q: op for q, op in term.map.items() if op != "I"}
        k = "I" if not clean else " ".join(f"{op}{q}" for q, op in sorted(clean.items()))
        d[k] = d.get(k, 0.0) + complex(term.coef)
    return d


def _openfermion_to_canonical_dict(h_of):
    """Convert OpenFermion QubitOperator into a canonical dict {pauli_string: coefficient}."""
    d = {}
    for term, coef in h_of.terms.items():
        if not term:
            k = "I"
        else:
            paulis = [f"{op}{q_idx}" for q_idx, op in term]
            paulis.sort(key=lambda x: int(x[1:]))
            k = " ".join(paulis)
        d[k] = d.get(k, 0.0) + complex(coef)
    return d


def test_jordan_wigner_vs_openfermion():
    """Cross-validate Ket's Jordan-Wigner mapping against OpenFermion."""
    of = pytest.importorskip("openfermion")
    from openfermion import FermionOperator, jordan_wigner as of_jw

    p = Process()
    q = p.alloc(4)

    # 1. Hopping term: a^†_0 a_1
    f_ket = Fermion({(0, 0, "a"): "+", (1, 1, "a"): "-"})
    f_of = FermionOperator("0^ 1")
    d_ket = _ket_to_canonical_dict(jordan_wigner(f_ket, q))
    d_of = _openfermion_to_canonical_dict(of_jw(f_of))
    assert d_ket == d_of

    # 2. Number operator: a^†_2 a_2
    f_ket_num = Fermion({(0, 2, "a"): "+", (1, 2, "a"): "-"})
    f_of_num = FermionOperator("2^ 2")
    d_ket_num = _ket_to_canonical_dict(jordan_wigner(f_ket_num, q))
    d_of_num = _openfermion_to_canonical_dict(of_jw(f_of_num))
    assert d_ket_num == d_of_num


def test_bravyi_kitaev_vs_openfermion():
    """Cross-validate Ket's Bravyi-Kitaev mapping against OpenFermion."""
    of = pytest.importorskip("openfermion")
    from openfermion import FermionOperator, bravyi_kitaev as of_bk

    p = Process()
    q = p.alloc(4)

    # Hopping term: a^†_0 a_1
    f_ket = Fermion({(0, 0, "a"): "+", (1, 1, "a"): "-"})
    f_of = FermionOperator("0^ 1")
    d_ket = _ket_to_canonical_dict(bravyi_kitaev(f_ket, q, tree=True))
    d_of = _openfermion_to_canonical_dict(of_bk(f_of, n_qubits=4))
    assert d_ket == d_of


def test_symmetry_conserving_bravyi_kitaev_vs_openfermion():
    """Cross-validate Ket's Symmetry-Conserving Bravyi-Kitaev (SCBK) mapping against OpenFermion."""
    of = pytest.importorskip("openfermion")
    from openfermion import FermionOperator, symmetry_conserving_bravyi_kitaev as of_scbk

    p = Process()
    q = p.alloc(4)

    # Reordered hopping term: a^†_0 a_2 + a^†_1 a_3
    f_ket = FermionSentence({
        Fermion({(0, 0, "a"): "+", (1, 2, "a"): "-"}): 1.0,
        Fermion({(0, 1, "a"): "+", (1, 3, "a"): "-"}): 1.0
    })
    f_of = FermionOperator("0^ 2") + FermionOperator("1^ 3")
    
    d_ket = _ket_to_canonical_dict(symmetry_conserving_bravyi_kitaev(f_ket, q, active_orbitals=4, n_alpha=1, n_beta=1))
    d_of = _openfermion_to_canonical_dict(of_scbk(f_of, active_orbitals=4, active_fermions=2))
    assert d_ket == d_of


