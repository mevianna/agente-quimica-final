# SPDX-FileCopyrightText: 2026 Maria Eduarda W. M. Vianna <maria.vianna@grad.ufsc.br>
# SPDX-FileCopyrightText: 2026 Erico Souza Teixeira <erico.teixeira@venturus.org.br>
#
# SPDX-License-Identifier: Apache-2.0

"""Electronic structure calculations and molecular integrals using PySCF."""

from dataclasses import dataclass
import numpy as np
from .basis_transformation import transform_integrals_1e, transform_integrals_2e

__all__ = [
    "MolecularData",
    "run_scf",
]


@dataclass
class MolecularData:
    """Dataclass storing molecular parameters and MO integrals."""

    n_electrons: int
    n_orbitals: int
    energy_nuc: float
    mo_coeff: np.ndarray
    one_mo: np.ndarray
    two_mo: np.ndarray


# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
def run_scf(
    symbols: list[str] | tuple[str, ...],
    coordinates: list[tuple[float, float, float]],
    charge: int = 0,
    mult: int = 1,
    basis: str = "sto-3g",
    method: str = "rhf",
    mo_coeff: np.ndarray | None = None,
) -> MolecularData:
    """Execute classical Hartree-Fock calculation and return molecular integrals.

    Args:
        symbols: Atomic symbols list (e.g., ['H', 'H']).
        coordinates: Atomic coordinates in Angstrom.
        charge: Net molecular charge.
        mult: Spin multiplicity (2S + 1).
        basis: Atomic orbital basis set (e.g., 'sto-3g').
        method: Mean-field method ('rhf' or 'rohf').
        mo_coeff: Optional custom molecular orbital coefficient matrix.
            If None, the canonical Hartree-Fock coefficients are used.

    Returns:
        MolecularData: Dataclass containing electrons, orbitals, nuclear energy,
            MO coefficients, and 1e/2e MO integrals.
    """
    try:
        import pyscf  # pylint: disable=import-outside-toplevel
    except ImportError as e:
        raise ImportError(
            "The 'pyscf' and 'numpy' packages are required for this function. "
            "Please install them using: pip install pyscf numpy"
        ) from e

    if not isinstance(symbols, (list, tuple)):
        raise TypeError("symbols must be a list or tuple of chemical symbols.")

    geometry = "; ".join(
        f"{sym} {coords[0]} {coords[1]} {coords[2]}"
        for sym, coords in zip(symbols, coordinates)
    )

    mol = pyscf.gto.Mole()
    mol.atom = geometry
    mol.basis = basis
    mol.charge = charge
    mol.spin = mult - 1
    mol.verbose = 0
    mol.build()

    method_str = method.strip().lower()
    if method_str == "rhf":
        mf = pyscf.scf.RHF(mol)
    elif method_str == "rohf":
        mf = pyscf.scf.ROHF(mol)
    else:
        raise ValueError(
            f"Unsupported method: '{method}'. Choose from 'rhf', 'rohf'."
        )

    mf.verbose = 0
    mf.kernel()

    if mo_coeff is None:
        if isinstance(mf.mo_coeff, (list, tuple)) or (
            isinstance(mf.mo_coeff, np.ndarray) and mf.mo_coeff.ndim == 3
        ):
            raise NotImplementedError(
                "Unrestricted methods with different spatial orbitals for alpha "
                "and beta are not currently supported."
            )
        coeff = mf.mo_coeff
    else:
        coeff = mo_coeff

    one_ao = mol.intor_symmetric("int1e_kin") + mol.intor_symmetric("int1e_nuc")
    two_ao = mol.intor("int2e_sph")

    one_mo = transform_integrals_1e(one_ao, coeff)
    two_mo = transform_integrals_2e(two_ao, coeff)
    energy_nuc = float(mf.energy_nuc())

    return MolecularData(
        n_electrons=mol.nelectron,
        n_orbitals=mol.nao,
        energy_nuc=energy_nuc,
        mo_coeff=coeff,
        one_mo=one_mo,
        two_mo=two_mo,
    )
