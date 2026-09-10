# SPDX-FileCopyrightText: 2026 Maria Eduarda W. M. Vianna <maria.vianna@grad.ufsc.br>
# SPDX-FileCopyrightText: 2026 Erico Souza Teixeira <erico.teixeira@venturus.org.br>
#
# SPDX-License-Identifier: Apache-2.0

"""Orbital basis transformations for 1-electron and 2-electron molecular integrals."""

import numpy as np

__all__ = [
    "transform_integrals_1e",
    "transform_integrals_2e",
]


def transform_integrals_1e(one_ao: np.ndarray, mo_coeff: np.ndarray) -> np.ndarray:
    """Transform 1-electron atomic orbital (AO) integrals to a molecular orbital (MO) basis.

    h_{ij} = sum_{p, q} C_{pi} h_{pq} C_{qj}

    Args:
        one_ao: 2D array of 1-electron integrals in AO basis.
        mo_coeff: Molecular orbital coefficient matrix C.

    Returns:
        np.ndarray: 2D array of 1-electron integrals in the transformed basis.
    """
    return np.einsum("pi,pq,qj->ij", mo_coeff, one_ao, mo_coeff)


def transform_integrals_2e(two_ao: np.ndarray, mo_coeff: np.ndarray) -> np.ndarray:
    """Transform 2-electron atomic orbital (AO) repulsion integrals to a molecular orbital (MO)
    basis.

    (ij|kl) = sum_{p, q, r, s} C_{pi} C_{qj} C_{rk} C_{sl} (pq|rs)

    Args:
        two_ao: 4D array of 2-electron integrals in AO basis (chemist notation).
        mo_coeff: Molecular orbital coefficient matrix C.

    Returns:
        np.ndarray: 4D array of 2-electron integrals in the transformed basis.
    """
    try:
        import pyscf.ao2mo  # pylint: disable=import-outside-toplevel
        return pyscf.ao2mo.incore.full(two_ao, mo_coeff)
    except ImportError as e:
        raise ImportError(
            "The 'pyscf' package is required for 2-electron integral transformation. "
            "Please install it using: pip install pyscf"
        ) from e
