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


def _serialize_fermion(term: Any) -> dict[str, Any]:
    """Serialize one ordered Ket fermionic product without relying on display text."""
    operators = [
        {
            "orbital": operator.orbital,
            "spin": operator.spin,
            "action": "creation" if operator.action == "+" else "annihilation",
            "symbol": operator.action,
        }
        for operator in term.operators
    ]
    notation = " ".join(
        f"a_{operator.orbital}{'†' if operator.action == '+' else ''}" for operator in term.operators
    ) or "I"
    return {"notation": notation, "operators": operators}


def _serialize_fermion_sentence(sentence: Any) -> list[dict[str, Any]]:
    """Serialize a Ket FermionSentence, including identity and complex coefficients."""
    terms = []
    for term, raw_coefficient in sentence.items():
        coefficient = complex(raw_coefficient)
        terms.append(
            {
                "coefficient": {"real": coefficient.real, "imag": coefficient.imag},
                **_serialize_fermion(term),
            }
        )
    return terms


MAPPING_LABELS = {
    "jordan_wigner": "Jordan–Wigner",
    "parity": "Parity",
    "bravyi_kitaev": "Bravyi–Kitaev",
}


def _mapping_lesson(orbital: int, action: str, mapping: str) -> dict[str, Any]:
    """Build deterministic learning material for a calculation performed by Ket."""
    operation = "criação" if action == "+" else "aniquilação"
    constructor = "CreateFermion" if action == "+" else "AnnihilateFermion"
    return {
        "available": True,
        "title": "Aprenda a encontrar este resultado no Ket",
        "steps": [
            f"Crie o operador de {operation} no orbital {orbital} com {constructor}.",
            f"Aloque {orbital + 1} qubit(s), pois os orbitais são indexados a partir de zero.",
            f"Aplique o mapeamento {MAPPING_LABELS[mapping]} fornecido por ket.chem.",
            "Percorra os termos retornados pelo Ket para consultar coeficientes e operadores de Pauli.",
        ],
        "code": "\n".join(
            [
                "from ket import Process",
                f"from ket.chem import {constructor}, {mapping}",
                "",
                "process = Process()",
                f"qubits = process.alloc({orbital + 1})",
                f"operator = {constructor}({orbital})",
                f"result = {mapping}(operator, qubits)",
                "",
                "for term in result.terms:",
                "    print(term.coef, term.map)",
            ]
        ),
    }


def _fermion_lesson(orbitals: list[int], actions: list[str], spins: list[str], operation: str) -> dict[str, Any]:
    """Build deterministic learning material for an operation performed by fermion.py."""
    constructors = ["CreateFermion" if action == "+" else "AnnihilateFermion" for action in actions]
    factor_lines = [
        f"    {constructor}({orbital}, spin={spin!r}),"
        for constructor, orbital, spin in zip(constructors, orbitals, spins)
    ]
    code = [
        "from ket.chem import AnnihilateFermion, CreateFermion, FermionSentence",
        "",
        "factors = [",
        *factor_lines,
        "]",
        "operator = factors[0]",
        "for factor in factors[1:]:",
        "    operator = operator * factor",
    ]
    steps = [
        "Crie cada operador de criação ou aniquilação com seu orbital e spin.",
        "Multiplique os fatores na mesma ordem em que aparecem no pedido.",
    ]
    if operation == "adjoint":
        code.extend(["", "result = operator.adjoint()", "print(result)"])
        steps.append("Chame adjoint(); o Ket inverte a ordem e troca criação por aniquilação, e vice-versa.")
    elif operation == "normal_order":
        code.extend(["", "result = operator.normal_ordered()", "print(result)"])
        steps.append("Chame normal_ordered(); o Ket aplica as relações de anticomutação e simplifica o resultado.")
    elif operation == "conservation":
        code.extend(
            [
                "",
                "sentence = FermionSentence({operator: 1})",
                "print(sentence.conserves_particle_number())",
                "print(sentence.conserves_spin_z())",
            ]
        )
        steps.append("Promova o produto a FermionSentence e consulte as verificações de conservação do Ket.")
    else:
        code.extend(["", "result = operator", "print(result)"])
        steps.append("Consulte o produto construído pelo Ket, preservando a ordem dos fatores.")
    return {
        "available": True,
        "title": "Aprenda a encontrar este resultado no Ket",
        "steps": steps,
        "code": "\n".join(code),
    }


def fermion_algebra(
    orbitals: list[int],
    actions: list[str],
    operation: str = "product",
    spins: list[str] | None = None,
) -> dict[str, Any]:
    """Run fermionic product, adjoint, normal ordering, or conservation checks with Ket.

    Args:
        orbitals: Ordered zero-based orbital indices.
        actions: Ordered actions, using '+' for creation and '-' for annihilation.
        operation: One of product, adjoint, normal_order, or conservation.
        spins: Optional ordered spin labels ('a' or 'b'); Ket infers them when omitted.
    """
    if not orbitals or len(orbitals) != len(actions):
        raise ValueError("orbitals and actions must be non-empty lists of the same length")
    if any(not isinstance(orbital, int) or isinstance(orbital, bool) or orbital < 0 for orbital in orbitals):
        raise ValueError("all orbitals must be non-negative integers")
    if any(action not in {"+", "-"} for action in actions):
        raise ValueError("all actions must be '+' (creation) or '-' (annihilation)")
    operations = {"product", "adjoint", "normal_order", "conservation"}
    if operation not in operations:
        raise ValueError(f"operation must be one of: {', '.join(sorted(operations))}")
    if spins is not None and len(spins) != len(orbitals):
        raise ValueError("spins must have the same length as orbitals")
    if spins is not None and any(spin not in {"a", "b"} for spin in spins):
        raise ValueError("all spins must be 'a' (alpha) or 'b' (beta)")

    _enable_local_ket()
    from ket.chem import AnnihilateFermion, CreateFermion, FermionSentence  # pylint: disable=import-outside-toplevel

    factors = []
    for index, (orbital, action) in enumerate(zip(orbitals, actions)):
        spin = None if spins is None else spins[index]
        constructor = CreateFermion if action == "+" else AnnihilateFermion
        factors.append(constructor(orbital, spin=spin))
    operator = factors[0]
    for factor in factors[1:]:
        operator = operator * factor

    resolved_spins = [factor.operators[0].spin for factor in factors]
    result: dict[str, Any] = {
        "calculation_status": "completed",
        "calculation_engine": "local Ket library",
        "calculation_provider": "Ket",
        "calculation_badge": "Calculado com Ket",
        "calculation_type": f"fermion_{operation}",
        "operation": operation,
        "orbitals": list(orbitals),
        "actions": list(actions),
        "spins": resolved_spins,
        "input_term": _serialize_fermion(operator),
        "education": _fermion_lesson(orbitals, actions, resolved_spins, operation),
    }
    sentence = FermionSentence({operator: 1})
    if operation == "product":
        result["result_terms"] = _serialize_fermion_sentence(sentence)
    elif operation == "adjoint":
        result["result_terms"] = _serialize_fermion_sentence(FermionSentence({operator.adjoint(): 1}))
    elif operation == "normal_order":
        result["result_terms"] = _serialize_fermion_sentence(operator.normal_ordered())
    else:
        result["conserves_particle_number"] = sentence.conserves_particle_number()
        result["conserves_spin_z"] = sentence.conserves_spin_z()
        result["is_two_body_number_conserving"] = sentence.is_two_body_number_conserving()
    return result


def mapping_example(orbital: int, action: str, mapping: str = "jordan_wigner") -> dict[str, Any]:
    """Map one fermionic creation or annihilation operator to Pauli terms.

    Args:
        orbital: Zero-based orbital index.
        action: Use '+' for creation and '-' for annihilation.
        mapping: One of jordan_wigner, parity, or bravyi_kitaev.
    """
    if orbital < 0:
        raise ValueError("orbital must be non-negative")
    if action not in {"+", "-"}:
        raise ValueError("action must be '+' (creation) or '-' (annihilation)")

    _enable_local_ket()
    from ket import Process  # pylint: disable=import-outside-toplevel
    from ket.chem import (  # pylint: disable=import-outside-toplevel
        AnnihilateFermion,
        CreateFermion,
        bravyi_kitaev,
        jordan_wigner,
        parity,
    )

    mappers = {
        "jordan_wigner": jordan_wigner,
        "parity": parity,
        "bravyi_kitaev": bravyi_kitaev,
    }
    if mapping not in mappers:
        raise ValueError(f"mapping must be one of: {', '.join(mappers)}")

    process = Process()
    qubits = process.alloc(orbital + 1)
    operator = CreateFermion(orbital) if action == "+" else AnnihilateFermion(orbital)
    hamiltonian = mappers[mapping](operator, qubits)
    return {
        "calculation_status": "completed",
        "calculation_engine": "local Ket library",
        "calculation_provider": "Ket",
        "calculation_badge": "Calculado com Ket",
        "calculation_type": "fermion_mapping",
        "input": f"a_{orbital}{'†' if action == '+' else ''}",
        "action": "creation" if action == "+" else "annihilation",
        "mapping": mapping,
        "mapping_label": MAPPING_LABELS[mapping],
        "qubits_required": orbital + 1,
        "pauli_terms": _serialize_hamiltonian(hamiltonian),
        "education": _mapping_lesson(orbital, action, mapping),
    }


def jordan_wigner_creation(orbital: int) -> dict[str, Any]:
    """Calculate the Ket Jordan-Wigner mapping for a fermionic creation operator.

    Args:
        orbital: Zero-based orbital index of the creation operator.

    Returns:
        The exact Pauli terms and coefficients computed by Ket.
    """
    return mapping_example(orbital=orbital, action="+", mapping="jordan_wigner")


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
        "calculation_status": "completed",
        "calculation_engine": "local Ket library",
        "calculation_provider": "Ket",
        "calculation_badge": "Calculado com Ket",
        "calculation_type": "molecular_hamiltonian",
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
        "name": "fermion_algebra",
        "description": "Usa a biblioteca Ket para construir produtos fermiônicos, calcular adjuntos, colocar em ordem normal ou verificar conservação de partículas e spin. Use em vez de calcular essas operações no texto.",
        "parameters": {
            "type": "object",
            "properties": {
                "orbitals": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Orbitais na ordem dos fatores, começando em zero.",
                },
                "actions": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["+", "-"]},
                    "description": "Uma ação por orbital: + para criação e - para aniquilação.",
                },
                "operation": {
                    "type": "string",
                    "enum": ["product", "adjoint", "normal_order", "conservation"],
                },
                "spins": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["a", "b"]},
                    "description": "Opcional: spin a (alfa) ou b (beta) para cada fator.",
                },
            },
            "required": ["orbitals", "actions", "operation"],
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
        functions = {
            "mapping_example": mapping_example,
            "fermion_algebra": fermion_algebra,
            "molecular_hamiltonian": molecular_hamiltonian,
        }
        if name not in functions:
            raise ValueError(f"Unknown tool: {name}")
        return json.dumps(functions[name](**json.loads(arguments)), ensure_ascii=False)
    except (ValueError, TypeError, RuntimeError) as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)
