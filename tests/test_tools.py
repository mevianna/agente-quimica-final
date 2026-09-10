"""Tests that do not require an LLM key or PySCF."""

import json

from quantum_chem_agent.tools import call_tool, jordan_wigner_creation, mapping_example


def test_jordan_wigner_mapping_uses_local_ket():
    result = mapping_example(1, "+")
    assert result["qubits_required"] == 2
    assert result["mapping"] == "jordan_wigner"
    assert len(result["pauli_terms"]) == 2


def test_tool_errors_are_json():
    result = json.loads(call_tool("mapping_example", '{"orbital": -1, "action": "+"}'))
    assert "error" in result


def test_explicit_jordan_wigner_creation_tool():
    result = jordan_wigner_creation(3)
    assert result["calculation_status"] == "completed"
    assert result["calculation_engine"] == "local Ket library"
    assert result["qubits_required"] == 4
    assert len(result["pauli_terms"]) == 2
