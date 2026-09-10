# SPDX-FileCopyrightText: 2026 Maria Eduarda W. M. Vianna <maria.vianna@grad.ufsc.br>
# SPDX-FileCopyrightText: 2026 Erico Souza Teixeira <erico.teixeira@venturus.org.br>
#
# SPDX-License-Identifier: Apache-2.0

"""Educational example: Variational Quantum Eigensolver (VQE) for H2 using PySCF, Ket, and SciPy.

This tutorial demonstrates a complete VQE pipeline in Ket matching PennyLane's workflow 1:1:
1. Definition of geometry and basis set for the Hydrogen molecule (H2).
2. Construction of the fermionic Hamiltonian in second quantization via PySCF.
3. Mapping of the fermionic Hamiltonian to Pauli qubit operators via Jordan-Wigner.
4. Construction of a 1-parameter Double Excitation quantum ansatz circuit.
5. Optimization of circuit parameters using scipy.optimize.minimize to find the ground state energy.
"""

import numpy as np
from scipy.optimize import minimize
import ket
from ket.chem import fermionic_hamiltonian, jordan_wigner


def prepare_hf_state(q):
    """Prepare initial Hartree-Fock state |1100> (2 electrons occupying the first 2 spin-orbitals)."""
    ket.X(q[0])
    ket.X(q[1])


def ansatz(params, q):
    """Variational Double Excitation ansatz applied on top of the initial Hartree-Fock state."""
    # 1. Prepare initial Hartree-Fock state |1100>
    prepare_hf_state(q)

    # 2. Double Excitation (mixes |1100> and |0011>)
    theta = params[0]

    ket.X(q[0])
    ket.RY(theta, q[0])
    ket.CNOT(q[0], q[1])

    ket.X(q[0])
    ket.X(q[1])
    ket.CNOT(q[0], q[2])
    ket.CNOT(q[1], q[3])
    ket.X(q[0])
    ket.X(q[1])


def main():
    # =========================================================================
    # STEP 1: Define physical system (H2 molecule at 0.74 Angstrom bond distance)
    # =========================================================================
    symbols = ["H", "H"]
    coordinates = [(0.0, 0.0, 0.0), (0.0, 0.0, 0.74)]
    basis = "sto-3g"

    print("=================================================================")
    print(" 1. VQE SETUP FOR HYDROGEN MOLECULE (H2)")
    print("=================================================================")
    print(f" Molecule:    {symbols[0]}-{symbols[1]}")
    print(f" Bond Length: 0.74 Angstrom")
    print(f" Basis Set:   {basis}")

    # =========================================================================
    # STEP 2: Generate Fermionic Hamiltonian
    # =========================================================================
    h_fermion = fermionic_hamiltonian(symbols, coordinates, basis=basis)
    print(f" Fermionic Terms: {len(h_fermion)}")

    # Total qubits needed for STO-3G H2 (4 spin-orbitals)
    num_qubits = 4

    # =========================================================================
    # STEP 3: Define Objective Function for VQE Optimization
    # =========================================================================
    energy_history = []

    def objective_function(params):
        """Evaluates the expectation value <psi(theta)|H|psi(theta)>."""
        p = ket.Process()
        q = p.alloc(num_qubits)

        # Map Hamiltonian to current process & qubits
        h_qubit = jordan_wigner(h_fermion, q)

        # Apply parametrized ansatz
        ansatz(params, q)

        # Compute expectation value of qubit Hamiltonian
        ev = ket.exp_value(h_qubit)
        energy = float(ev.get().real)

        # Track optimization history
        energy_history.append(energy)
        return energy

    # Initial trial parameters (1 parameter theta = 0.0 for Hartree-Fock state)
    initial_params = np.array([0.0])
    initial_energy = objective_function(initial_params)

    print(f" Initial Energy (Hartree-Fock state): {initial_energy:.6f} Ha")
    print("=================================================================")
    print(" 2. RUNNING OPTIMIZATION VIA SCI-PY (COBYLA)")
    print("=================================================================")

    # =========================================================================
    # STEP 4: Run Optimization with SciPy
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
    print("=================================================================")

    # Reference exact ground state energy for H2 at 0.74 Å in STO-3G is ~ -1.137306 Hartree
    exact_ref = -1.137306
    print(f" Reference Energy (FCI): {exact_ref:.6f} Ha")
    print(f" Energy Difference:      {abs(res.fun - exact_ref):.6f} Ha")
    print(f" Total steps recorded:  {len(energy_history)}")
    print("=================================================================")


if __name__ == "__main__":
    main()
