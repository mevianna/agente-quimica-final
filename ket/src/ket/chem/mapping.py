# SPDX-FileCopyrightText: 2026 Maria Eduarda W. M. Vianna <maria.vianna@grad.ufsc.br>
# SPDX-FileCopyrightText: 2026 José Carlos Libois <jose.libois@posgrad.ufsc.br>
# SPDX-FileCopyrightText: 2026 Erico Souza Teixeira <erico.teixeira@venturus.org.br>
#
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=protected-access

"""
Fermion-to-qubit mappings.


Currently implemented mappings:
    - Jordan-Wigner
    - Parity
    - Bravyi-Kitaev
    - Symmetry-Conserving Bravyi-Kitaev
"""

from ket.expv import Pauli, Hamiltonian
from .fermion import Fermion, FermionSentence

__all__ = ["jordan_wigner", "parity", "bravyi_kitaev", "symmetry_conserving_bravyi_kitaev"]

def _identity(process):
    return Hamiltonian(
        [Pauli(None, None, _process=process, _map={}, _coef=1.0)],
        process,
    )

def _jw_single(orbital: int, op: str, qubits):
    """
    Jordan-Wigner mapping of a single creation/annihilation operator.

    Args:
        orbital: orbital index
        op: '+' (creation) or '-' (annihilation)
        qubits: quantum register

    Returns:
        Hamiltonian
    """
    process = qubits.ket_process

    z_string = Pauli(None, None, _process=process, _map={}, _coef=1.0)
    for i in range(orbital):
        z_string = z_string * Pauli.z(qubits[i])

    x_term = 0.5 * Pauli.x(qubits[orbital])

    if op == "+":
        y_term = (-0.5j) * Pauli.y(qubits[orbital])

    elif op == "-":
        y_term = (0.5j) * Pauli.y(qubits[orbital])

    else:
        raise ValueError(f"invalid fermionic operator {op!r}")

    local = x_term + y_term
    return z_string @ local

def _parity_single(orbital: int, op: str, qubits):
    """
    Parity mapping of a single creation/annihilation operator.

    Args:
        orbital: orbital index
        op: '+' (creation) or '-' (annihilation)
        qubits: quantum register

    Returns:
        Hamiltonian
    """

    process = qubits.ket_process
    n_qubits = len(qubits)

    # X string on qubits < orbital
    x_string = Pauli(None, None, _process=process, _map={}, _coef=1.0)
    for i in range(orbital + 1, n_qubits):
        x_string = x_string * Pauli.x(qubits[i])

    # Z string on orbital - 1
    z_string = Pauli(None, None, _process=process, _map={}, _coef=1.0)
    if orbital > 0:
        z_string = Pauli.z(qubits[orbital - 1])

    x_term = 0.5 * (z_string @ Pauli.x(qubits[orbital]))

    if op == "+":
        y_term = (-0.5j) * Pauli.y(qubits[orbital])
    elif op == "-":
        y_term = (0.5j) * Pauli.y(qubits[orbital])
    else:
        raise ValueError(f"invalid fermionic operator {op!r}")

    local = x_term + y_term
    return x_string @ local

def _bk_single(orbital: int, op: str, qubits):
    """
    Bravyi-Kitaev mapping of a single creation/annihilation operator.

    Args:
        orbital: orbital index
        op: '+' (creation) or '-' (annihilation)
        qubits: quantum register

    Returns:
        Hamiltonian
    """

    process = qubits.ket_process
    n_qubits = len(qubits)

    # X string on update set
    x_string = Pauli(None, None, _process=process, _map={}, _coef=1.0)
    k = orbital | (orbital + 1)
    while k < n_qubits:
        x_string = x_string * Pauli.x(qubits[k])
        k = k | (k + 1)

    # Z string on parity set for X term
    z_string_x = Pauli(None, None, _process=process, _map={}, _coef=1.0)
    k = orbital - 1
    while k >= 0:
        z_string_x = z_string_x * Pauli.z(qubits[k])
        k = (k & (k + 1)) - 1

    # Z string on parity set (excluding flip set) for Y term
    z_string_y = Pauli(None, None, _process=process, _map={}, _coef=1.0)
    k = orbital - 1
    while k >= 0:
        if (k | (k + 1)) != orbital:
            z_string_y = z_string_y * Pauli.z(qubits[k])
        k = (k & (k + 1)) - 1

    x_term = 0.5 * (z_string_x @ Pauli.x(qubits[orbital]))

    if op == "+":
        y_term = (-0.5j) * (z_string_y @ Pauli.y(qubits[orbital]))
    elif op == "-":
        y_term = (0.5j) * (z_string_y @ Pauli.y(qubits[orbital]))
    else:
        raise ValueError(f"invalid fermionic operator {op!r}")

    local = x_term + y_term
    return x_string @ local

def _map_word(word, qubits, single_mapper):
    """
    Maps a single Fermion word into a qubit Hamiltonian.

    Applies a chosen fermionic-to-qubit mapping strategy
    (e.g., Jordan-Wigner or Parity) to each operator in the word,
    and composes the resulting Hamiltonian via operator product.

    Args:
        word (Fermion): Fermionic operator word (ordered product of creation/annihilation ops).
        qubits: Quantum register used for the mapping.
        single_mapper (callable): Function mapping a single (orbital, op, qubits)
            into a Hamiltonian term.

    Returns:
        Hamiltonian: Mapped qubit Hamiltonian for the full fermionic word.
    """
    process = qubits.ket_process
    result = _identity(process)

    for op in word.operators:
        orbital = op.orbital
        action = op.action
        if orbital >= len(qubits):
            raise ValueError(
                f"orbital {orbital} requires at least {orbital + 1} qubits"
            )

        result = result @ single_mapper(orbital, action, qubits)

    return result

def _fermion_mapping(operator, qubits, single_mapper):
    """
    Generic fermion-to-qubit mapping dispatcher.

    Applies a given single-operator mapping strategy to either:
    - a Fermion (single word), or
    - a FermionSentence (linear combination of words).

    This function factors out common logic between mappings such as
    Jordan-Wigner and Parity.

    Args:
        operator (Fermion | FermionSentence): Fermionic operator(s) to map.
        qubits: Quantum register used for the mapping.
        single_mapper (callable): Function that maps a single operator
            (orbital, op, qubits) -> Hamiltonian.

    Returns:
        Hamiltonian: Qubit Hamiltonian representing the fermionic operator.

    Raises:
        TypeError: If `operator` is not Fermion or FermionSentence.
    """
    if isinstance(operator, Fermion):
        return _map_word(operator, qubits, single_mapper)

    if isinstance(operator, FermionSentence):
        process = qubits.ket_process
        result = Hamiltonian([], process)

        for word, coef in operator.items():
            result += coef * _map_word(word, qubits, single_mapper)

        return result

    raise TypeError("operator must be Fermion or FermionSentence")

def jordan_wigner(operator, qubits):
    """
    Applies the Jordan-Wigner transformation to a fermionic operator.

    Args:
        operator (Fermion | FermionSentence): Fermionic operator(s) to map.
        qubits: Quantum register.

    Returns:
        Hamiltonian: Qubit Hamiltonian in the Jordan-Wigner representation.
    """
    return _fermion_mapping(operator, qubits, _jw_single)

def parity(operator, qubits):
    """
    Applies the parity transformation to a fermionic operator.

    Args:
        operator (Fermion | FermionSentence): Fermionic operator(s) to map.
        qubits: Quantum register.

    Returns:
        Hamiltonian: Qubit Hamiltonian in the parity representation.
    """
    return _fermion_mapping(operator, qubits, _parity_single)

def bravyi_kitaev(operator, qubits, tree: bool = True):
    """
    Applies the Bravyi-Kitaev transformation to a fermionic operator.

    Args:
        operator (Fermion | FermionSentence): Fermionic operator(s) to map.
        qubits: Quantum register.
        tree: If True (default), uses the Fenwick tree-based mapping (same tree
            as symmetry-conserving Bravyi-Kitaev). If False, uses the standard
            bitwise Bravyi-Kitaev mapping.

    Returns:
        Hamiltonian: Qubit Hamiltonian in the Bravyi-Kitaev representation.
    """
    if tree:
        tree_data = _build_scbk_tree(len(qubits))
        def _bk_tree_single(orbital: int, op: str, q):
            return _scbk_single(orbital, op, q, tree_data)
        return _fermion_mapping(operator, qubits, _bk_tree_single)
    return _fermion_mapping(operator, qubits, _bk_single)

def _build_scbk_tree(size: int):
    """
    Builds the parent and children structures recursively.

    Args:
        size: Total number of qubits/modes in the system.

    Returns:
        tuple[dict, dict]: (parent, children) where parent maps each node
        to its parent index (or None), and children maps each node to a
        list of its child indices.
    """
    parent = {i: None for i in range(size)}
    children = {i: [] for i in range(size)}

    if size > 0:
        root = size - 1

        def fenwick_recurse(left, right, p_node):
            if left >= right:
                return

            pivot = (left + right) >> 1

            parent[pivot] = p_node
            children[p_node].append(pivot)

            fenwick_recurse(left, pivot, pivot)
            fenwick_recurse(pivot + 1, right, p_node)

        fenwick_recurse(0, size - 1, root)

    return parent, children

def _scbk_update_set(j: int, parent: dict) -> list[int]:
    """
    Finds the set of ancestors (update set) of node j in the Fenwick tree.

    Args:
        j: Target node index.
        parent: Map of node indices to their parent index.

    Returns:
        list[int]: Ancestor node indices sorted from parent to root.
    """
    res = []
    curr = parent.get(j)
    while curr is not None:
        res.append(curr)
        curr = parent.get(curr)
    return res

def _scbk_remainder_set(j: int, parent: dict, children: dict) -> list[int]:
    """
    Finds the remainder set of node j, which contains the child indices
    less than j of all ancestors of j.

    Args:
        j: Target node index.
        parent: Map of node indices to their parent index.
        children: Map of node indices to lists of their child indices.

    Returns:
        list[int]: Node indices in the remainder set.
    """
    res = []
    ancestors = _scbk_update_set(j, parent)
    for a in ancestors:
        for c in children.get(a, []):
            if c < j:
                res.append(c)
    return res

def _scbk_parity_set(j: int, parent: dict, children: dict) -> list[int]:
    """
    Finds the parity set of node j, which is the union of the remainder set
    and the direct children set of node j.

    Args:
        j: Target node index.
        parent: Map of node indices to their parent index.
        children: Map of node indices to lists of their child indices.

    Returns:
        list[int]: Node indices in the parity set.
    """
    return _scbk_remainder_set(j, parent, children) + children.get(j, [])

def _scbk_single(orbital: int, op: str, qubits, tree_data: tuple):
    """
    Maps a single creation/annihilation fermionic operator using the
    symmetry-conserving Bravyi-Kitaev (SCBK) Fenwick tree data.

    Args:
        orbital: Target orbital index.
        op: '+' (creation) or '-' (annihilation).
        qubits: Quantum register.
        tree_data: Pre-computed tree tuple (parent, children).

    Returns:
        Hamiltonian: Qubit Hamiltonian term for the mapped operator.
    """
    process = qubits.ket_process
    parent, children = tree_data

    x_string = Pauli(None, None, _process=process, _map={}, _coef=1.0)
    for k in _scbk_update_set(orbital, parent):
        x_string = x_string * Pauli.x(qubits[k])

    z_string_x = Pauli(None, None, _process=process, _map={}, _coef=1.0)
    for k in _scbk_parity_set(orbital, parent, children):
        z_string_x = z_string_x * Pauli.z(qubits[k])

    z_string_y = Pauli(None, None, _process=process, _map={}, _coef=1.0)
    for k in _scbk_remainder_set(orbital, parent, children):
        z_string_y = z_string_y * Pauli.z(qubits[k])

    x_term = 0.5 * (z_string_x @ Pauli.x(qubits[orbital]))

    if op == "+":
        y_term = (-0.5j) * (z_string_y @ Pauli.y(qubits[orbital]))
    elif op == "-":
        y_term = (0.5j) * (z_string_y @ Pauli.y(qubits[orbital]))
    else:
        raise ValueError(f"invalid fermionic operator {op!r}")

    local = x_term + y_term
    return x_string @ local

def _apply_parity_and_reduce(hamiltonian: Hamiltonian,
                             target_qubit_id: int, parity_val: int) -> Hamiltonian:
    """
    Eliminates a target qubit by substituting its Z operators with the
    corresponding parity constant (+1 or -1), and shifts higher qubit indices
    down by one to prevent gaps. Re-composes operators on the same qubit
    using Pauli multiplication rules.

    Args:
        hamiltonian: Qubit Hamiltonian to reduce.
        target_qubit_id: Absolute ID of the target qubit to remove.
        parity_val: Parity eigenvalue constant (+1 or -1) to substitute.

    Returns:
        Hamiltonian: Reduced qubit Hamiltonian with the target qubit removed.
    """
    new_terms = []
    for term in hamiltonian.terms:
        coef_factor = 1.0
        if target_qubit_id in term.map:
            op = term.map[target_qubit_id]
            if op == "Z":
                coef_factor = parity_val

        # Reconstruct the Pauli term by composing single-qubit Paulis
        new_pauli = Pauli(None, None, _process=term.ket_process, _map={}, _coef=1.0)

        for q_idx, op_str in term.map.items():
            if q_idx == target_qubit_id:
                if op_str == "Z":
                    continue
                new_idx = q_idx
            else:
                new_idx = q_idx - 1 if q_idx > target_qubit_id else q_idx

            single_pauli = Pauli(None, None, _process=term.ket_process,
                                 _map={new_idx: op_str}, _coef=1.0)
            new_pauli = new_pauli @ single_pauli

        final_coef = term.coef * coef_factor * new_pauli.coef
        clean_map = {q: p for q, p in new_pauli.map.items() if p != "I"}
        new_terms.append(Pauli(None, None, _process=term.ket_process,
                               _map=clean_map, _coef=final_coef))

    result = Hamiltonian(new_terms, process=hamiltonian.ket_process)
    result._filter()
    return result


def symmetry_conserving_bravyi_kitaev(
    operator, qubits, active_orbitals: int, n_alpha: int, n_beta: int
):
    """
    Applies the symmetry-conserving Bravyi-Kitaev (SCBK) transformation,
    reordering spin orbitals to all-up then all-down, and removing two
    qubits based on total particle number and total spin conservation.

    Args:
        operator: Fermion or FermionSentence to transform.
        qubits: Quantum register.
        active_orbitals: Number of active orbitals.
        n_alpha: Number of active alpha (spin-up) fermions.
        n_beta: Number of active beta (spin-down) fermions.

    Returns:
        Hamiltonian: The symmetry-reduced qubit Hamiltonian.
    """
    if active_orbitals != len(qubits):
        raise ValueError("active_orbitals must match the length of the qubits register.")

    # Build the custom tree data ONCE for N orbitals
    tree_data = _build_scbk_tree(active_orbitals)

    # 1 & 2. Reorder spins (Up-then-Down) on the fly and apply SCBK mapping
    def _reordered_scbk_single(orbital: int, op: str, q):
        half_n = active_orbitals // 2
        if orbital % 2 == 0:
            new_orbital = orbital // 2
        else:
            new_orbital = half_n + (orbital // 2)

        # Pass the tree tuple down
        return _scbk_single(new_orbital, op, q, tree_data)

    # Reuses your generic mapping logic perfectly
    qubit_hamiltonian = _fermion_mapping(operator, qubits, _reordered_scbk_single)

    # 3. Calculate Parity Constants directly from n_alpha and n_beta
    parity_final = (-1)**(n_alpha + n_beta)
    parity_middle = (-1)**n_alpha

    # 4. Identify the absolute qubit IDs for Ket's backend
    middle_qubit_id = qubits[(active_orbitals // 2) - 1].qubits[0]
    final_qubit_id = qubits[active_orbitals - 1].qubits[0]

    # 5. Inject constants and reduce the Hamiltonian
    qubit_hamiltonian = _apply_parity_and_reduce(qubit_hamiltonian, middle_qubit_id, parity_middle)

    if final_qubit_id > middle_qubit_id:
        final_qubit_id -= 1

    qubit_hamiltonian = _apply_parity_and_reduce(qubit_hamiltonian, final_qubit_id, parity_final)

    return _group_hamiltonian_terms(qubit_hamiltonian)

def _group_hamiltonian_terms(hamiltonian: Hamiltonian) -> Hamiltonian:
    """Sum identical terms ignoring hidden identity (I) operators."""
    new_terms = {}
    for term in hamiltonian.terms:
        # Filter out 'I'
        clean_map = {q: p for q, p in term.map.items() if p != "I"}
        # Create grouping key
        key = "".join(f"{p}{q}" for q, p in sorted(clean_map.items()))

        if key not in new_terms:
            new_terms[key] = Pauli(None, None, _process=term.ket_process,
                                   _map=clean_map, _coef=term.coef)
        else:
            new_terms[key].coef += term.coef

    # Filter out zeros
    final_terms = [t for t in new_terms.values() if abs(t.coef) > 1e-10]
    return Hamiltonian(final_terms, process=hamiltonian.ket_process)
