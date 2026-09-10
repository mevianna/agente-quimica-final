# SPDX-FileCopyrightText: 2026 Maria Eduarda W. M. Vianna <maria.vianna@grad.ufsc.br>
# SPDX-FileCopyrightText: 2026 Erico Souza Teixeira <erico.teixeira@venturus.org.br>
#
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for native UCCSD implementation in Ket."""

import math
import numpy as np
import pytest
from scipy.optimize import minimize

import ket
from ket import Process
from ket.chem import (
    UCCSDResult,
    UCCSDResources,
    generate_excitations,
    build_fermionic_generators,
    build_jw_uccsd_generators,
    build_uccsd_ansatz,
    apply_uccsd,
    get_uccsd_resources,
)


def test_generate_excitations_h2():
    """Test excitation generation for H2 (2 electrons, 4 spin-orbitals)."""
    singles, doubles = generate_excitations(n_electrons=2, n_spin_orbitals=4)

    assert len(singles) == 2
    assert singles == [(0, 2), (1, 3)]

    assert len(doubles) == 1
    assert doubles == [(0, 1, 2, 3)]


def test_generate_excitations_active_space_4_8():
    """Test excitation generation for 4 active electrons, 8 spin-orbitals."""
    singles, doubles = generate_excitations(n_electrons=4, n_spin_orbitals=8)

    assert len(singles) == 8
    assert len(doubles) == 18


def test_build_fermionic_generators():
    """Test construction of anti-Hermitian fermionic generators."""
    singles, doubles = generate_excitations(n_electrons=2, n_spin_orbitals=4)
    generators = build_fermionic_generators(singles, doubles)

    assert len(generators) == 3

    # Check that each generator G is anti-Hermitian (G^dagger = -G)
    for g in generators:
        g_adj = g.adjoint()
        g_sum = g + g_adj
        g_sum.simplify(tol=1e-10)
        assert len(g_sum) == 0, "Generator G is not anti-Hermitian"


def test_build_jw_uccsd_ansatz():
    """Test full UCCSD ansatz compilation with Jordan-Wigner."""
    p = Process()
    q = p.alloc(4)

    ansatz = build_uccsd_ansatz(n_electrons=2, n_spin_orbitals=4, qubits=q, mapping="JW")

    assert isinstance(ansatz, UCCSDResult)
    assert ansatz.mapping == "JW"
    assert ansatz.n_singles == 2
    assert ansatz.n_doubles == 1
    assert len(ansatz) == 3

    # Check that mapped operators are Hermitian (coefficients are purely real)
    for op in ansatz.operators:
        for term in op.terms:
            assert abs(term.coef.imag) < 1e-10
            assert len(term.map) > 0


def test_uccsd_resources():
    """Test resource estimation for H2 UCCSD circuit."""
    p = Process()
    q = p.alloc(4)

    ansatz = build_uccsd_ansatz(n_electrons=2, n_spin_orbitals=4, qubits=q, mapping="JW")
    resources = get_uccsd_resources(ansatz, n_qubits=4, trotter_steps=1)

    assert isinstance(resources, UCCSDResources)
    assert resources.n_qubits == 4
    assert resources.n_generators == 3
    # Single excitations have 2 Pauli terms each, double excitation has 8 Pauli terms -> 2 + 2 + 8 = 12 terms
    assert resources.total_pauli_terms == 12
    assert resources.pauli_rotations == 12
    assert resources.cnot > 0
    assert resources.total_gates > 0


def test_vqe_h2_with_uccsd():
    """Test a full VQE optimization on H2 using native Ket UCCSD."""
    n_qubits = 4
    n_electrons = 2

    # Standard STO-3G H2 qubit Hamiltonian (at bond length R = 0.7414 Å)
    def make_h2_hamiltonian(q):
        with ket.obs():
            h = (
                -0.81054
                + 0.17218 * ket.Z(q[0])
                + 0.17218 * ket.Z(q[1])
                - 0.22575 * ket.Z(q[2])
                - 0.22575 * ket.Z(q[3])
                + 0.12091 * ket.Z(q[0]) * ket.Z(q[1])
                + 0.16893 * ket.Z(q[0]) * ket.Z(q[2])
                + 0.16893 * ket.Z(q[1]) * ket.Z(q[3])
                + 0.17464 * ket.Z(q[2]) * ket.Z(q[3])
                + 0.16615 * ket.Z(q[0]) * ket.Z(q[3])
                + 0.16615 * ket.Z(q[1]) * ket.Z(q[2])
                + 0.04523 * (
                    ket.X(q[0]) * ket.X(q[1]) * ket.Y(q[2]) * ket.Y(q[3])
                    + ket.Y(q[0]) * ket.Y(q[1]) * ket.X(q[2]) * ket.X(q[3])
                    - ket.X(q[0]) * ket.Y(q[1]) * ket.Y(q[2]) * ket.X(q[3])
                    - ket.Y(q[0]) * ket.X(q[1]) * ket.X(q[2]) * ket.Y(q[3])
                )
            )
        return h

    # Objective function for VQE
    def cost_function(params):
        p = Process()
        q = p.alloc(n_qubits)

        # Prepare Hartree-Fock state |1100>
        ket.X(q[0])
        ket.X(q[1])

        # Build and apply UCCSD ansatz
        ansatz = build_uccsd_ansatz(n_electrons, n_qubits, qubits=q, mapping="JW")
        apply_uccsd(params, ansatz, q, trotter_steps=1)

        # Measure expectation value of the Hamiltonian
        h_qubit = make_h2_hamiltonian(q)
        ev = ket.exp_value(h_qubit)
        return float(ev.get().real)

    # Initial parameters (all zeros -> Hartree-Fock state)
    initial_params = np.zeros(3)
    hf_energy = cost_function(initial_params)

    # Optimize with SciPy COBYLA
    res = minimize(cost_function, initial_params, method="COBYLA", options={"maxiter": 100})

    # Optimized energy is lower than HF, and converges to the ground state of the test Hamiltonian
    assert res.fun < hf_energy
    assert math.isclose(res.fun, -2.0013, abs_tol=1e-3)
