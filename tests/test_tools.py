"""Tests that do not require an LLM key or PySCF."""

import json

from quantum_chem_agent.tools import call_tool, fermion_algebra, jordan_wigner_creation, mapping_example


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


def test_fermion_product_is_built_by_local_ket():
    result = fermion_algebra([0, 1], ["+", "-"], "product")

    assert result["calculation_provider"] == "Ket"
    assert result["calculation_type"] == "fermion_product"
    assert result["input_term"]["notation"] == "a_0† a_1"
    assert result["result_terms"][0]["operators"][0]["action"] == "creation"
    assert result["result_terms"][0]["operators"][1]["action"] == "annihilation"


def test_fermion_adjoint_reverses_order_and_actions():
    result = fermion_algebra([0, 1], ["+", "-"], "adjoint")

    assert result["result_terms"][0]["notation"] == "a_1† a_0"
    assert result["education"]["available"] is True
    assert "adjoint()" in result["education"]["code"]


def test_fermion_normal_order_uses_anticommutation():
    result = fermion_algebra([0, 0], ["-", "+"], "normal_order", spins=["a", "a"])
    terms = {term["notation"]: term["coefficient"]["real"] for term in result["result_terms"]}

    assert terms == {"I": 1.0, "a_0† a_0": -1.0}
    assert "normal_ordered()" in result["education"]["code"]


def test_fermion_conservation_is_checked_by_ket():
    conserving = fermion_algebra([0, 2], ["+", "-"], "conservation")
    spin_flip = fermion_algebra([0, 1], ["+", "-"], "conservation")

    assert conserving["conserves_particle_number"] is True
    assert conserving["conserves_spin_z"] is True
    assert spin_flip["conserves_particle_number"] is True
    assert spin_flip["conserves_spin_z"] is False
