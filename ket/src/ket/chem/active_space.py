# SPDX-FileCopyrightText: 2026 Maria Eduarda W. M. Vianna <maria.vianna@grad.ufsc.br>
# SPDX-FileCopyrightText: 2026 Erico Souza Teixeira <erico.teixeira@venturus.org.br>
#
# SPDX-License-Identifier: Apache-2.0

"""Active space selection and frozen-core reduction."""

from dataclasses import dataclass
import numpy as np

__all__ = [
    "ActiveSpaceData",
    "active_space",
]


@dataclass
class ActiveSpaceData:
    """Dataclass storing effective core energy and active space integrals."""

    core_energy: float
    one_active: np.ndarray
    two_active: np.ndarray
    n_active_orbitals: int


# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
def active_space(
    n_electrons: int,
    n_orbitals: int,
    energy_nuc: float,
    one_mo: np.ndarray,
    two_mo: np.ndarray,
    active_electrons: int | None = None,
    active_orbitals: int | None = None,
) -> ActiveSpaceData:
    """Select active space around the HOMO/LUMO window.

    Args:
        n_electrons: Total number of electrons.
        n_orbitals: Total number of spatial molecular orbitals.
        energy_nuc: Nuclear repulsion energy.
        one_mo: 1-electron MO integrals matrix.
        two_mo: 2-electron MO integrals tensor.
        active_electrons: Number of active electrons (if None, all electrons are active).
        active_orbitals: Number of active spatial orbitals (if None, all orbitals are active).

    Returns:
        ActiveSpaceData: Dataclass with core energy and active integral arrays.
    """
    if active_electrons is None:
        active_electrons = n_electrons
    if active_orbitals is None:
        active_orbitals = n_orbitals

    if active_electrons > n_electrons:
        raise ValueError(
            "active_electrons cannot be larger than the total number of electrons."
        )
    if active_orbitals > n_orbitals:
        raise ValueError(
            "active_orbitals cannot be larger than the total number of spatial orbitals."
        )

    n_core_orbitals = (n_electrons - active_electrons) // 2
    core = list(range(n_core_orbitals))
    active = list(range(n_core_orbitals, n_core_orbitals + active_orbitals))

    core_constant = float(energy_nuc)
    one_mo_renorm = one_mo.copy()

    if core:
        for i in core:
            core_constant += 2.0 * one_mo_renorm[i, i]
            for j in core:
                core_constant += 2.0 * two_mo[i, i, j, j] - two_mo[i, j, j, i]

        for p in active:
            for q in active:
                for i in core:
                    one_mo_renorm[p, q] += 2.0 * two_mo[i, i, p, q] - two_mo[i, p, i, q]

    one_active = one_mo_renorm[np.ix_(active, active)]
    two_active = two_mo[np.ix_(active, active, active, active)]

    return ActiveSpaceData(
        core_energy=core_constant,
        one_active=one_active,
        two_active=two_active,
        n_active_orbitals=len(active),
    )
