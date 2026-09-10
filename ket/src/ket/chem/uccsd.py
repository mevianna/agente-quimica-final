# SPDX-FileCopyrightText: 2026 Maria Eduarda W. M. Vianna <maria.vianna@grad.ufsc.br>
# SPDX-FileCopyrightText: 2026 Erico Souza Teixeira <erico.teixeira@venturus.org.br>
#
# SPDX-License-Identifier: Apache-2.0

"""Public UCCSD construction and quantum circuit interface for Ket.

This module provides native Ket tools for constructing Unitary Coupled Cluster
Singles and Doubles (UCCSD) variational ansatzes for quantum chemistry (VQE).

It supports:
- Automatic single and double excitation generation with spin conservation (ΔSz = 0).
- Native second-quantization anti-Hermitian fermionic generator creation.
- Extensible fermion-to-qubit mappings (starting with Jordan-Wigner).
- Conversion to Hermitian generators (A = iG) for variational simulation.
- Circuit synthesis using CNOT cascades and single-qubit rotations.
- Gate resource estimation and circuit statistics.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from math import pi
from typing import Any, Callable

import ket
from ket.base import Process, Quant
from ket.expv import Hamiltonian, Pauli

from .fermion import AnnihilateFermion, CreateFermion, FermionSentence
from .mapping import jordan_wigner

__all__ = [
    "UCCSDResult",
    "UCCSDResources",
    "generate_excitations",
    "build_fermionic_generators",
    "build_jw_uccsd_generators",
    "build_uccsd_ansatz",
    "apply_pauli_generator",
    "apply_uccsd",
    "get_uccsd_resources",
]


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass(frozen=True)
class UCCSDResult:
    """Store mapped UCCSD generators and construction statistics."""

    mapping: str
    operators: tuple[Hamiltonian, ...]
    n_singles: int
    n_doubles: int
    n_initial_generators: int
    n_symmetry_discarded: int = 0
    n_zero_discarded: int = 0

    def __len__(self) -> int:
        return len(self.operators)

    def __iter__(self):
        return iter(self.operators)

    def __getitem__(self, index: int) -> Hamiltonian:
        return self.operators[index]


@dataclass(frozen=True)
class UCCSDResources:
    """Store estimated quantum resource counts for the UCCSD circuit."""

    n_qubits: int
    n_generators: int
    total_pauli_terms: int
    average_terms_per_generator: float
    average_pauli_weight: float
    maximum_pauli_weight: int
    pauli_rotations: int
    cnot: int
    hadamard: int
    rx: int
    ry: int
    rz: int
    total_gates: int
    depth: int


# =============================================================================
# EXCITATIONS & FERMIONIC GENERATORS
# =============================================================================

def generate_excitations(
    n_electrons: int,
    n_spin_orbitals: int,
    delta_sz: int = 0,
) -> tuple[list[tuple[int, int]], list[tuple[int, int, int, int]]]:
    """Generate spin-conserving single and double excitation orbital indices.

    Orbitals with even indices (0, 2, 4, ...) are assigned spin-alpha (spin up),
    and odd indices (1, 3, 5, ...) are assigned spin-beta (spin down).

    Args:
        n_electrons: Number of active electrons (occupied spin-orbitals 0 .. n_electrons - 1).
        n_spin_orbitals: Total number of active spin-orbitals (virtuals n_electrons .. n_spin_orbitals - 1).
        delta_sz: Change in total spin projection Sz (default 0).

    Returns:
        tuple containing:
        - singles: list of (occupied, virtual) index pairs.
        - doubles: list of (occupied_1, occupied_2, virtual_1, virtual_2) index tuples.
    """
    occupied = list(range(n_electrons))
    virtual = list(range(n_electrons, n_spin_orbitals))

    # 1. Single Excitations: p -> q (with spin conservation)
    singles: list[tuple[int, int]] = []
    for p in occupied:
        for q in virtual:
            # Spin conservation: p and q must have same spin (even/odd parity)
            if (q % 2) - (p % 2) == delta_sz:
                singles.append((p, q))

    # 2. Double Excitations: (p1, p2) -> (q1, q2)
    doubles: list[tuple[int, int, int, int]] = []
    for p1, p2 in combinations(occupied, 2):
        for q1, q2 in combinations(virtual, 2):
            # Spin conservation: (sz(q1) + sz(q2)) - (sz(p1) + sz(p2)) == delta_sz
            spin_p = (p1 % 2) + (p2 % 2)
            spin_q = (q1 % 2) + (q2 % 2)
            if spin_q - spin_p == delta_sz:
                doubles.append((p1, p2, q1, q2))

    return singles, doubles


def build_fermionic_generators(
    singles: list[tuple[int, int]],
    doubles: list[tuple[int, int, int, int]],
) -> list[FermionSentence]:
    """Build anti-Hermitian fermionic excitation generators G = T - T^dagger.

    Args:
        singles: Single excitation pairs (occupied, virtual).
        doubles: Double excitation tuples (occupied_1, occupied_2, virtual_1, virtual_2).

    Returns:
        A list of anti-Hermitian FermionSentence instances.
    """
    generators: list[FermionSentence] = []

    # Single excitation generators: a_q^† a_p - a_p^† a_q
    for occupied, virtual in singles:
        term_fwd = CreateFermion(virtual) * AnnihilateFermion(occupied)
        term_rev = CreateFermion(occupied) * AnnihilateFermion(virtual)
        g_single = FermionSentence({term_fwd: 1.0, term_rev: -1.0})
        generators.append(g_single)

    # Double excitation generators: a_q2^† a_q1^† a_p2 a_p1 - a_p1^† a_p2^† a_q1 a_q2
    for occupied_1, occupied_2, virtual_1, virtual_2 in doubles:
        term_fwd = (
            CreateFermion(virtual_2)
            * CreateFermion(virtual_1)
            * AnnihilateFermion(occupied_2)
            * AnnihilateFermion(occupied_1)
        )
        term_rev = (
            CreateFermion(occupied_1)
            * CreateFermion(occupied_2)
            * AnnihilateFermion(virtual_1)
            * AnnihilateFermion(virtual_2)
        )
        g_double = FermionSentence({term_fwd: 1.0, term_rev: -1.0})
        generators.append(g_double)

    return generators


# =============================================================================
# QUBIT MAPPING & OPERATOR PREPARATION
# =============================================================================

def _prepare_mapped_generator(
    qubit_generator: Hamiltonian,
    tolerance: float = 1e-10,
) -> Hamiltonian | None:
    """Convert an anti-Hermitian qubit generator G into a Hermitian operator A = iG.

    The variational quantum circuit evolves as exp(-i * theta * A) = exp(theta * G).
    This function multiplies by 1j and filters out negligible / zero terms.

    Args:
        qubit_generator: Anti-Hermitian Hamiltonian mapped to qubits.
        tolerance: Numerical threshold to discard small terms.

    Returns:
        Hermitian Hamiltonian with real coefficients, or None if it vanishes.
    """
    # Convert G (anti-Hermitian) to A = 1j * G (Hermitian)
    hermitian_op = 1j * qubit_generator

    # Filter terms: keep non-identity terms with significant coefficient
    valid_terms: list[Pauli] = []
    for term in hermitian_op.terms:
        # Ignore identity terms (no active qubits in map)
        active_map = {q: p for q, p in term.map.items() if p != "I"}
        coef_real = term.coef.real

        if abs(coef_real) > tolerance and len(active_map) > 0:
            # Construct cleaned Pauli term with strictly real coefficient
            clean_term = Pauli(
                None,
                None,
                _process=term.ket_process,
                _map=active_map,
                _coef=coef_real,
            )
            valid_terms.append(clean_term)

    if not valid_terms:
        return None

    result = Hamiltonian(valid_terms, process=qubit_generator.ket_process)
    result._filter()
    return result if len(result.terms) > 0 else None


def build_jw_uccsd_generators(
    fermionic_generators: list[FermionSentence],
    qubits: Quant,
) -> tuple[list[Hamiltonian], int, int]:
    """Map fermionic generators to qubits using Jordan-Wigner.

    Args:
        fermionic_generators: List of fermionic excitation generators (G = T - T^dagger).
        qubits: Quantum register allocated in the current Ket process.

    Returns:
        tuple of (operators, symmetry_discarded, zero_discarded).
    """
    operators: list[Hamiltonian] = []
    zero_discarded = 0
    symmetry_discarded = 0

    for f_gen in fermionic_generators:
        mapped_h = jordan_wigner(f_gen, qubits)
        prep_h = _prepare_mapped_generator(mapped_h)

        if prep_h is None:
            zero_discarded += 1
            continue

        operators.append(prep_h)

    return operators, symmetry_discarded, zero_discarded


def build_uccsd_ansatz(
    n_electrons: int,
    n_spin_orbitals: int,
    qubits: Quant | None = None,
    mapping: str = "JW",
    verbose: bool = False,
) -> UCCSDResult:
    """Build a mapped UCCSD ansatz from electron and spin-orbital counts.

    Args:
        n_electrons: Number of active electrons in the molecule.
        n_spin_orbitals: Total number of active spin-orbitals.
        qubits: Optional Ket Quant register. If None, allocates a temporary register.
        mapping: Qubit mapping strategy. Currently supports 'JW' (Jordan-Wigner).
        verbose: If True, prints construction summary statistics.

    Returns:
        UCCSDResult containing mapped Hermitian generators and metadata.
    """
    mapping_upper = mapping.upper()

    if qubits is None:
        p = Process()
        qubits = p.alloc(n_spin_orbitals)

    # 1. Generate single and double excitations
    singles, doubles = generate_excitations(n_electrons, n_spin_orbitals)

    # 2. Build anti-Hermitian fermionic generators
    fermionic_gens = build_fermionic_generators(singles, doubles)

    # 3. Map to qubits according to selected mapping strategy
    if mapping_upper in {"JW", "JORDAN_WIGNER", "JORDAN-WIGNER"}:
        operators, sym_disc, zero_disc = build_jw_uccsd_generators(fermionic_gens, qubits)
        resolved_mapping = "JW"
    else:
        raise ValueError(
            f"Unsupported mapping '{mapping}'. Currently supported: 'JW' (Jordan-Wigner)."
        )

    result = UCCSDResult(
        mapping=resolved_mapping,
        operators=tuple(operators),
        n_singles=len(singles),
        n_doubles=len(doubles),
        n_initial_generators=len(singles) + len(doubles),
        n_symmetry_discarded=sym_disc,
        n_zero_discarded=zero_disc,
    )

    if verbose:
        print("==================================================")
        print(" UCCSD Ansatz Construction Summary (Ket Native)")
        print("==================================================")
        print(f" Mapping:                    {result.mapping}")
        print(f" Single excitations:         {result.n_singles}")
        print(f" Double excitations:         {result.n_doubles}")
        print(f" Initial generators:         {result.n_initial_generators}")
        print(f" Final active generators:    {len(result)}")
        print(f" Symmetry discarded:         {result.n_symmetry_discarded}")
        print(f" Zero discarded:             {result.n_zero_discarded}")
        print("==================================================")

    return result


# =============================================================================
# QUANTUM CIRCUIT SYNTHESIS (PAULI ROTATIONS & UCCSD)
# =============================================================================

def apply_pauli_generator(
    theta: float,
    generator: Hamiltonian,
    qubits: Quant,
    trotter_steps: int = 1,
) -> None:
    """Apply one Hermitian UCCSD generator exp(-i * theta * A) via Trotterized Pauli rotations.

    For each Pauli string P_j with coefficient c_j, the rotation exp(-i * phi/2 * P_j)
    is synthesized using basis changes (H for X, RX(-π/2) for Y), a CNOT ladder,
    and an RZ(phi) gate, where phi = 2.0 * c_j * theta / trotter_steps.

    Args:
        theta: Variational parameter for this generator.
        generator: Hermitian Hamiltonian generator (A = iG).
        qubits: Ket Quant register to apply the quantum gates on.
        trotter_steps: Number of Trotter product steps (default 1).
    """
    for _ in range(trotter_steps):
        for term in generator.terms:
            coef = term.coef.real
            if abs(coef) < 1e-10:
                continue

            active_map = {q: p for q, p in term.map.items() if p != "I"}
            if not active_map:
                continue

            # Rotation angle: exp(-i * (phi / 2) * P) = exp(-i * (c_j * theta / r) * P)
            phi = 2.0 * coef * theta / trotter_steps

            # List of active (qubit_id, pauli_type)
            sorted_ops = sorted(active_map.items(), key=lambda item: item[0])
            active_q_indices = [q_idx for q_idx, _ in sorted_ops]
            active_qubits = [qubits[q_idx] for q_idx in active_q_indices]

            # Single-qubit rotation optimization
            if len(active_qubits) == 1:
                target_q = active_qubits[0]
                pauli_char = sorted_ops[0][1]
                if pauli_char == "X":
                    ket.RX(phi, target_q)
                elif pauli_char == "Y":
                    ket.RY(phi, target_q)
                elif pauli_char == "Z":
                    ket.RZ(phi, target_q)
                continue

            # Multi-qubit Pauli string rotation:
            # 1. Basis transformation to Z
            for q_idx, pauli_char in sorted_ops:
                q = qubits[q_idx]
                if pauli_char == "X":
                    ket.H(q)
                elif pauli_char == "Y":
                    ket.RX(-pi / 2, q)

            # 2. Entanglement CNOT ladder
            for i in range(len(active_qubits) - 1):
                ket.CNOT(active_qubits[i], active_qubits[i + 1])

            # 3. Core Z-rotation on target qubit
            ket.RZ(phi, active_qubits[-1])

            # 4. Uncompute CNOT ladder
            for i in reversed(range(len(active_qubits) - 1)):
                ket.CNOT(active_qubits[i], active_qubits[i + 1])

            # 5. Uncompute basis transformation
            for q_idx, pauli_char in sorted_ops:
                q = qubits[q_idx]
                if pauli_char == "X":
                    ket.H(q)
                elif pauli_char == "Y":
                    ket.RX(pi / 2, q)


def apply_uccsd(
    params: list[float] | tuple[float, ...] | Any,
    ansatz: UCCSDResult,
    qubits: Quant,
    trotter_steps: int = 1,
) -> None:
    """Apply all UCCSD variational excitation gates in sequence on the quantum register.

    Args:
        params: Sequence of variational parameters (one per active generator).
        ansatz: Compiled UCCSDResult containing the mapped generators.
        qubits: Ket Quant register to apply the quantum circuit on.
        trotter_steps: Number of Trotter steps for generator exponentials (default 1).
    """
    if len(params) != len(ansatz.operators):
        raise ValueError(
            f"Number of parameters ({len(params)}) does not match "
            f"number of active generators ({len(ansatz.operators)})."
        )

    for theta, generator in zip(params, ansatz.operators):
        apply_pauli_generator(theta, generator, qubits, trotter_steps=trotter_steps)


# =============================================================================
# RESOURCE ESTIMATION & CIRCUIT METRICS
# =============================================================================

def get_uccsd_resources(
    ansatz: UCCSDResult,
    n_qubits: int,
    trotter_steps: int = 1,
) -> UCCSDResources:
    """Estimate gate counts and quantum circuit resources for the UCCSD ansatz.

    Args:
        ansatz: Compiled UCCSDResult.
        n_qubits: Number of qubits in the register.
        trotter_steps: Number of Trotter steps used per generator.

    Returns:
        UCCSDResources with detailed gate counts and statistics.
    """
    total_pauli_terms = 0
    weights: list[int] = []

    cnot_count = 0
    hadamard_count = 0
    rx_count = 0
    ry_count = 0
    rz_count = 0

    for generator in ansatz.operators:
        for term in generator.terms:
            active_map = {q: p for q, p in term.map.items() if p != "I"}
            if not active_map or abs(term.coef) < 1e-10:
                continue

            w = len(active_map)
            total_pauli_terms += 1
            weights.append(w)

            n_x = sum(1 for p in active_map.values() if p == "X")
            n_y = sum(1 for p in active_map.values() if p == "Y")
            n_z = sum(1 for p in active_map.values() if p == "Z")

            if w == 1:
                if n_x:
                    rx_count += 1
                elif n_y:
                    ry_count += 1
                elif n_z:
                    rz_count += 1
            else:
                cnot_count += 2 * (w - 1)
                hadamard_count += 2 * n_x
                rx_count += 2 * n_y
                rz_count += 1

    # Scale gate counts by trotter steps
    cnot_count *= trotter_steps
    hadamard_count *= trotter_steps
    rx_count *= trotter_steps
    ry_count *= trotter_steps
    rz_count *= trotter_steps

    n_gen = len(ansatz.operators)
    avg_terms = total_pauli_terms / n_gen if n_gen else 0.0
    avg_weight = sum(weights) / total_pauli_terms if total_pauli_terms else 0.0
    max_weight = max(weights) if weights else 0
    total_gates = cnot_count + hadamard_count + rx_count + ry_count + rz_count
    depth = total_gates  # Upper bound estimate on sequential depth

    return UCCSDResources(
        n_qubits=n_qubits,
        n_generators=n_gen,
        total_pauli_terms=total_pauli_terms,
        average_terms_per_generator=avg_terms,
        average_pauli_weight=avg_weight,
        maximum_pauli_weight=max_weight,
        pauli_rotations=total_pauli_terms * trotter_steps,
        cnot=cnot_count,
        hadamard=hadamard_count,
        rx=rx_count,
        ry=ry_count,
        rz=rz_count,
        total_gates=total_gates,
        depth=depth,
    )
