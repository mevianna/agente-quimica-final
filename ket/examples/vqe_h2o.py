# SPDX-FileCopyrightText: 2026 Maria Eduarda W. M. Vianna <maria.vianna@grad.ufsc.br>
# SPDX-FileCopyrightText: 2026 Erico Souza Teixeira <erico.teixeira@venturus.org.br>
#
# SPDX-License-Identifier: Apache-2.0

"""Educational example: Variational Quantum Eigensolver (VQE) for H2O (Water) using PySCF, Ket, and SciPy.

This tutorial demonstrates a VQE pipeline for the Water molecule (H2O):
1. Definition of geometry (O-H bond length 0.957 Å, angle 104.5 degrees).
2. Active space selection (4 active electrons in 4 active spatial orbitals -> 8 qubits).
3. Construction of the fermionic Hamiltonian in second quantization via PySCF.
4. Mapping to Pauli qubit operators via Jordan-Wigner transformation.
5. Optimization of a parametrized ansatz circuit using scipy.optimize.minimize (COBYLA).
"""

import numpy as np
from scipy.optimize import minimize
import ket
from ket.chem import fermionic_hamiltonian, jordan_wigner


def ansatz(params, q, num_qubits=8):
    """Hardware-Efficient Ansatz for H2O active space (8 qubits).

    Prepares Hartree-Fock reference state |11110000> (4 active electrons in 4 active orbitals)
    and applies single-qubit RY rotations and CNOT entanglers.
    """
    # Prepare Hartree-Fock state for 4 active electrons (|11110000>)
    for i in range(4):
        ket.X(q[i])

    # Layer 1: Parametrized RY rotations
    for i in range(num_qubits):
        ket.RY(params[i], q[i])

    # Layer 2: Entangling CNOT cascade
    for i in range(num_qubits - 1):
        ket.CNOT(q[i], q[i + 1])

    # Layer 3: Second layer of RY rotations
    for i in range(num_qubits):
        ket.RY(params[num_qubits + i], q[i])


def main():
    # =========================================================================
    # STEP 1: Define H2O molecule geometry
    # =========================================================================
    symbols = ["O", "H", "H"]
    coordinates = [
        (0.0, 0.0, 0.1173),
        (0.0, 0.7572, -0.4692),
        (0.0, -0.7572, -0.4692),
    ]
    basis = "sto-3g"

    # Active space: 4 active electrons in 4 active spatial orbitals (8 qubits)
    active_electrons = 4
    active_orbitals = 4
    num_qubits = 2 * active_orbitals  # 8 qubits

    print("=================================================================")
    print(" 1. VQE SETUP FOR WATER MOLECULE (H2O)")
    print("=================================================================")
    print(f" Molecule:          O-H-H")
    print(f" Basis Set:         {basis}")
    print(f" Active Electrons:  {active_electrons}")
    print(f" Active Orbitals:   {active_orbitals}")
    print(f" Qubits Required:   {num_qubits}")

    # =========================================================================
    # STEP 2: Generate Fermionic Hamiltonian with Active Space
    # =========================================================================
    h_fermion = fermionic_hamiltonian(
        symbols,
        coordinates,
        basis=basis,
        active_electrons=active_electrons,
        active_orbitals=active_orbitals,
    )
    print(f" Fermionic Terms:   {len(h_fermion)}")

    # =========================================================================
    # STEP 3: Define Objective Function for VQE Optimization
    # =========================================================================
    energy_history = []

    def objective_function(params):
        """Evaluates expectation value <psi(params)|H|psi(params)>."""
        p = ket.Process()
        q = p.alloc(num_qubits)

        # Map Hamiltonian to process & qubits
        h_qubit = jordan_wigner(h_fermion, q)

        # Apply parametrized ansatz
        ansatz(params, q, num_qubits=num_qubits)

        # Compute expectation value
        ev = ket.exp_value(h_qubit)
        energy = float(ev.get().real)

        energy_history.append(energy)
        return energy

    # 16 parameters for 8-qubit 2-layer HEA ansatz (initially zero -> Hartree-Fock state)
    initial_params = np.zeros(16)
    initial_energy = objective_function(initial_params)

    print(f" Initial Energy (Hartree-Fock state): {initial_energy:.6f} Ha")
    print("=================================================================")
    print(" 2. RUNNING OPTIMIZATION VIA SCI-PY (COBYLA)")
    print("=================================================================")

    # =========================================================================
    # STEP 4: Run Optimization with SciPy COBYLA
    # =========================================================================
    res = minimize(
        objective_function,
        initial_params,
        method="COBYLA",
    )

    print(" Optimization complete!")
    print(f" Successful:       {res.success}")
    print(f" Iterations/Evals: {res.nfev}")
    print(f" Final VQE Energy: {res.fun:.6f} Ha")
    print(f" Total Energy Drop: {initial_energy - res.fun:.6f} Ha")
    print(f" Total steps recorded: {len(energy_history)}")
    print("=================================================================")


if __name__ == "__main__":
    main()
