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
    assert result["calculation_provider"] == "Ket"
    assert result["calculation_badge"] == "Calculado com Ket"
    assert result["qubits_required"] == 4
    assert len(result["pauli_terms"]) == 2


def test_mapping_includes_ket_learning_material():
    result = mapping_example(2, "-", "bravyi_kitaev")
    lesson = result["education"]
    assert lesson["available"] is True
    assert lesson["title"] == "Aprenda a encontrar este resultado no Ket"
    assert len(lesson["steps"]) == 4
    assert "AnnihilateFermion(2)" in lesson["code"]
    assert "bravyi_kitaev(operator, qubits)" in lesson["code"]
