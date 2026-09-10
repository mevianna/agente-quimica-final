# SPDX-FileCopyrightText: 2026 Maria Eduarda W. M. Vianna <maria.vianna@grad.ufsc.br>
# SPDX-FileCopyrightText: 2026 Erico Souza Teixeira <erico.teixeira@venturus.org.br>
#
# SPDX-License-Identifier: Apache-2.0

"""Educational example: Molecular Hamiltonian Generation and Mapping using PySCF and Ket.

This tutorial demonstrates the complete quantum chemistry workflow in Ket:
1. Definition of geometry and orbital basis set for the Hydrogen molecule (H2).
2. Construction of the Fermionic Hamiltonian in second quantization.
3. Qubit allocation and mapping to Pauli operators via the Jordan-Wigner transformation.
"""

from ket import Process
from ket.chem import fermionic_hamiltonian, jordan_wigner


def main():
    # =========================================================================
    # STEP 1: Define the parameters for the Hydrogen molecule (H2)
    # =========================================================================
    # Chemical symbols for the atoms
    symbols = ["H", "H"]

    # Cartesian coordinates in Angstrom (bond distance H-H of 0.74 Angstrom)
    coordinates = [(0.0, 0.0, 0.0), (0.0, 0.0, 0.74)]

    # Atomic orbital basis set (STO-3G minimal basis set)
    basis = "sto-3g"

    print("=================================================================")
    print(" 1. MOLECULE DEFINITION")
    print("=================================================================")
    print(f" Molecule:   {symbols[0]}-{symbols[1]}")
    print(f" Distance:   0.74 Angstrom")
    print(f" Basis:      {basis}")
    print()

    # =========================================================================
    # STEP 2: Generate the Fermionic Hamiltonian in Second Quantization
    # =========================================================================
    # The fermionic_hamiltonian function uses PySCF to solve the electronic
    # structure (RHF) and builds the second-quantized FermionSentence.
    h_fermion = fermionic_hamiltonian(symbols, coordinates, basis=basis)

    print("=================================================================")
    print(" 2. FERMIONIC HAMILTONIAN (SECOND QUANTIZATION)")
    print("=================================================================")
    print(f" Number of fermionic terms: {len(h_fermion)}")
    print("\nGenerated fermionic terms:")
    print(h_fermion)
    print()

    # =========================================================================
    # STEP 3: Allocate Qubits and Apply Jordan-Wigner Mapping
    # =========================================================================
    # Determine the number of spin-orbitals (qubits) required by inspecting
    # the maximum orbital index in the fermionic terms (4 qubits for H2 in STO-3G).
    num_qubits = max(
        op.orbital
        for term in h_fermion
        for op in term.operators
        if term.operators
    ) + 1

    # Create the quantum process and allocate the required qubits
    p = Process()
    qubits = p.alloc(num_qubits)

    # Transform the Fermionic Hamiltonian to a Qubit Hamiltonian via Jordan-Wigner
    h_qubit = jordan_wigner(h_fermion, qubits)

    print("=================================================================")
    print(" 3. QUBIT HAMILTONIAN (JORDAN-WIGNER MAPPING)")
    print("=================================================================")
    print(f" Allocated qubits:             {num_qubits}")
    print(f" Number of Pauli terms:        {len(h_qubit.terms)}")
    print("\nQubit Pauli terms:")
    print(h_qubit)
    print("=================================================================")


if __name__ == "__main__":
    main()
