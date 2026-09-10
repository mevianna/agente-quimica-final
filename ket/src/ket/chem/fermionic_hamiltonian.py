# SPDX-FileCopyrightText: 2026 Maria Eduarda W. M. Vianna <maria.vianna@grad.ufsc.br>
# SPDX-FileCopyrightText: 2026 Erico Souza Teixeira <erico.teixeira@venturus.org.br>
#
# SPDX-License-Identifier: Apache-2.0

"""Construct fermionic Hamiltonians for quantum chemistry systems."""

import numpy as np
from .fermion import Fermion, FermionSentence, CreateFermion, AnnihilateFermion
from .electronic_structure import run_scf
from .active_space import active_space

__all__ = [
    "one_body_fermion",
    "two_body_fermion",
    "fermionic_hamiltonian",
]


def one_body_fermion(
    one_body_integrals: np.ndarray,
    tol: float = 1e-12,
) -> FermionSentence:
    """Construct the fermionic 1-body operator from spatial orbital integrals.

    H_1 = sum_{p, q} h_{pq} (a⁺_{p, alpha} a_{q, alpha} + a⁺_{p, beta} a_{q, beta})

    Args:
        one_body_integrals: 2D array of 1-electron integrals h_pq.
        tol: Threshold to discard negligible terms.

    Returns:
        FermionSentence: Second-quantized 1-body fermionic operator.
    """
    fs = FermionSentence()
    n_orbitals = one_body_integrals.shape[0]

    for p in range(n_orbitals):
        for q in range(n_orbitals):
            val = one_body_integrals[p, q]
            if abs(val) >= tol:
                term_alpha = CreateFermion(2 * p, "a") * AnnihilateFermion(2 * q, "a")
                term_beta = CreateFermion(2 * p + 1, "b") * AnnihilateFermion(2 * q + 1, "b")

                fs[term_alpha] = fs.get(term_alpha, 0.0) + val
                fs[term_beta] = fs.get(term_beta, 0.0) + val

    return fs


# pylint: disable=too-many-nested-blocks
def two_body_fermion(
    two_body_integrals: np.ndarray,
    tol: float = 1e-12,
) -> FermionSentence:
    r"""Construct the fermionic 2-body operator from spatial orbital integrals.

    H_2 = -1/2 \sum_{pqrs} (pq|rs) \sum_{\sigma,\tau} a^\dagger_{p\sigma} a^\dagger_{r\tau}
          a_{q\sigma} a_{s\tau}

    Args:
        two_body_integrals: 4D array of 2-electron integrals (pq|rs) in chemist notation.
        tol: Threshold to discard negligible terms.

    Returns:
        FermionSentence: Second-quantized 2-body fermionic operator.
    """
    fs = FermionSentence()
    n_orbitals = two_body_integrals.shape[0]

    for p in range(n_orbitals):
        for q in range(n_orbitals):
            for r in range(n_orbitals):
                for s in range(n_orbitals):
                    val = two_body_integrals[p, q, r, s]
                    if abs(val) >= tol:
                        coef = -0.5 * val

                        # 1. (alpha, alpha)
                        t1 = (
                            CreateFermion(2 * p, "a")
                            * CreateFermion(2 * r, "a")
                            * AnnihilateFermion(2 * q, "a")
                            * AnnihilateFermion(2 * s, "a")
                        )
                        # 2. (alpha, beta)
                        t2 = (
                            CreateFermion(2 * p, "a")
                            * CreateFermion(2 * r + 1, "b")
                            * AnnihilateFermion(2 * q, "a")
                            * AnnihilateFermion(2 * s + 1, "b")
                        )
                        # 3. (beta, alpha)
                        t3 = (
                            CreateFermion(2 * p + 1, "b")
                            * CreateFermion(2 * r, "a")
                            * AnnihilateFermion(2 * q + 1, "b")
                            * AnnihilateFermion(2 * s, "a")
                        )
                        # 4. (beta, beta)
                        t4 = (
                            CreateFermion(2 * p + 1, "b")
                            * CreateFermion(2 * r + 1, "b")
                            * AnnihilateFermion(2 * q + 1, "b")
                            * AnnihilateFermion(2 * s + 1, "b")
                        )

                        for term in (t1, t2, t3, t4):
                            fs[term] = fs.get(term, 0.0) + coef

    return fs


# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
def fermionic_hamiltonian(
    symbols: list[str] | tuple[str, ...],
    coordinates: list[tuple[float, float, float]],
    charge: int = 0,
    mult: int = 1,
    basis: str = "sto-3g",
    method: str = "rhf",
    active_electrons: int | None = None,
    active_orbitals: int | None = None,
    mo_coeff: np.ndarray | None = None,
    tol: float = 1e-12,
) -> FermionSentence:
    """Generate the fermionic Hamiltonian of a physical system using PySCF.

    Args:
        symbols: A list of atomic symbols (e.g. ['H', 'H']).
        coordinates: List of atomic coordinates in Angstrom.
        charge: Net charge of the molecule.
        mult: Spin multiplicity (2S + 1).
        basis: Atomic orbital basis set (e.g., 'sto-3g', '6-31g').
        method: Mean-field method to run. Options: 'rhf', 'rohf'.
        active_electrons: Number of active electrons for the active space. If None,
            all electrons are active.
        active_orbitals: Number of active spatial orbitals for the active space. If None,
            all orbitals are active.
        mo_coeff: Optional custom molecular orbital coefficient matrix.
        tol: Tolerance threshold to discard negligible integral terms.

    Returns:
        FermionSentence: The fermionic Hamiltonian in second-quantized form.

    Examples:
        >>> H = fermionic_hamiltonian(
        ...     symbols=['H', 'H'],
        ...     coordinates=[(0.0, 0.0, 0.0), (0.0, 0.0, 0.74)],
        ...     basis='sto-3g'
        ... )
    """
    mol_data = run_scf(
        symbols=symbols,
        coordinates=coordinates,
        charge=charge,
        mult=mult,
        basis=basis,
        method=method,
        mo_coeff=mo_coeff,
    )

    as_data = active_space(
        n_electrons=mol_data.n_electrons,
        n_orbitals=mol_data.n_orbitals,
        energy_nuc=mol_data.energy_nuc,
        one_mo=mol_data.one_mo,
        two_mo=mol_data.two_mo,
        active_electrons=active_electrons,
        active_orbitals=active_orbitals,
    )

    fs = FermionSentence()
    if abs(as_data.core_energy) >= tol:
        fs[Fermion()] = as_data.core_energy

    h1 = one_body_fermion(as_data.one_active, tol=tol)
    h2 = two_body_fermion(as_data.two_active, tol=tol)

    for term, coef in h1.items():
        fs[term] = fs.get(term, 0.0) + coef

    for term, coef in h2.items():
        fs[term] = fs.get(term, 0.0) + coef

    fs.simplify(tol)
    return fs
