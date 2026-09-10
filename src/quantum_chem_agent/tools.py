"""Deterministic scientific tools exposed to the language model."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def _enable_local_ket() -> None:
    """Prefer the Ket copy included in this repository over a global install."""
    repository = Path(__file__).resolve().parents[2]
    ket_source = repository / "ket" / "src"
    if ket_source.is_dir() and str(ket_source) not in sys.path:
        sys.path.insert(0, str(ket_source))


def _serialize_hamiltonian(hamiltonian: Any) -> list[dict[str, Any]]:
    terms: list[dict[str, Any]] = []
    for term in hamiltonian.terms:
        coefficient = complex(term.coef)
        terms.append(
            {
                "coefficient": {"real": coefficient.real, "imag": coefficient.imag},
                "paulis": {str(qubit): pauli for qubit, pauli in term.map.items()},
            }
        )
    return terms


def mapping_example(orbital: int, action: str, mapping: str = "jordan_wigner") -> dict[str, Any]:
    """Map one creation/annihilation fermionic operator to Pauli terms."""
    if orbital < 0:
        raise ValueError("orbital must be non-negative")
    if action not in {"+", "-"}:
        raise ValueError("action must be '+' (creation) or '-' (annihilation)")

    _enable_local_ket()
    from ket import Process  # pylint: disable=import-outside-toplevel
    from ket.chem import Fermion, bravyi_kitaev, jordan_wigner, parity  # pylint: disable=import-outside-toplevel

    mappers = {
        "jordan_wigner": jordan_wigner,
        "parity": parity,
        "bravyi_kitaev": bravyi_kitaev,
    }
    if mapping not in mappers:
        raise ValueError(f"mapping must be one of: {', '.join(mappers)}")

    process = Process()
    qubits = process.alloc(orbital + 1)
    operator = Fermion({(0, orbital, "a"): action})
    hamiltonian = mappers[mapping](operator, qubits)
    return {
        "input": f"a_{orbital}{'†' if action == '+' else ''}",
        "mapping": mapping,
        "qubits_required": orbital + 1,
        "pauli_terms": _serialize_hamiltonian(hamiltonian),
    }


def molecular_hamiltonian(
    symbols: list[str], coordinates: list[list[float]], basis: str = "sto-3g", mapping: str = "jordan_wigner"
) -> dict[str, Any]:
    """Generate a molecular Hamiltonian; requires PySCF, normally under WSL2."""
    _enable_local_ket()
    try:
        import pyscf  # noqa: F401  # pylint: disable=import-outside-toplevel,unused-import
    except ImportError as exc:
        raise RuntimeError(
            "PySCF is unavailable. On Windows, run this calculation under WSL2 and install with "
            "pip install -e '.[chemistry]'. Mapping examples remain available without PySCF."
        ) from exc

    from ket import Process  # pylint: disable=import-outside-toplevel
    from ket.chem import bravyi_kitaev, fermionic_hamiltonian, jordan_wigner, parity  # pylint: disable=import-outside-toplevel

    mappers = {"jordan_wigner": jordan_wigner, "parity": parity, "bravyi_kitaev": bravyi_kitaev}
    if mapping not in mappers:
        raise ValueError(f"mapping must be one of: {', '.join(mappers)}")
    if len(symbols) != len(coordinates):
        raise ValueError("symbols and coordinates must have the same length")

    geometry = [tuple(point) for point in coordinates]
    fermionic = fermionic_hamiltonian(symbols, geometry, basis=basis)
    max_orbital = max(operator.orbital for term in fermionic for operator in term.operators)
    process = Process()
    qubits = process.alloc(max_orbital + 1)
    qubit_hamiltonian = mappers[mapping](fermionic, qubits)
    return {
        "molecule": symbols,
        "basis": basis,
        "mapping": mapping,
        "qubits_required": max_orbital + 1,
        "fermionic_terms": len(fermionic),
        "pauli_terms": _serialize_hamiltonian(qubit_hamiltonian),
    }


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "name": "mapping_example",
        "description": "Mapeia um operador fermiônico de criação ou aniquilação para termos de Pauli. Use para explicar Jordan-Wigner, parity ou Bravyi-Kitaev.",
        "parameters": {
            "type": "object",
            "properties": {
                "orbital": {"type": "integer", "description": "Índice do orbital, começando em zero."},
                "action": {"type": "string", "enum": ["+", "-"], "description": "+ para criação; - para aniquilação."},
                "mapping": {"type": "string", "enum": ["jordan_wigner", "parity", "bravyi_kitaev"]},
            },
            "required": ["orbital", "action"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "molecular_hamiltonian",
        "description": "Gera Hamiltoniano molecular usando PySCF e o mapeia para qubits. Requer PySCF no WSL2/Linux.",
        "parameters": {
            "type": "object",
            "properties": {
                "symbols": {"type": "array", "items": {"type": "string"}},
                "coordinates": {"type": "array", "items": {"type": "array", "items": {"type": "number"}}},
                "basis": {"type": "string"},
                "mapping": {"type": "string", "enum": ["jordan_wigner", "parity", "bravyi_kitaev"]},
            },
            "required": ["symbols", "coordinates"],
            "additionalProperties": False,
        },
    },
]


def call_tool(name: str, arguments: str) -> str:
    """Execute a model-requested tool and return a JSON result, including errors."""
    try:
        functions = {"mapping_example": mapping_example, "molecular_hamiltonian": molecular_hamiltonian}
        if name not in functions:
            raise ValueError(f"Unknown tool: {name}")
        return json.dumps(functions[name](**json.loads(arguments)), ensure_ascii=False)
    except (ValueError, TypeError, RuntimeError) as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)
