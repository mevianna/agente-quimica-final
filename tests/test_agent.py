"""Tests for structured calculation provenance without contacting an LLM."""

from quantum_chem_agent.agent import QuantumChemAgent, direct_mapping_result, parse_mapping_request
from quantum_chem_agent.tools import mapping_example


def test_reply_result_exposes_only_recorded_ket_calculations():
    agent = QuantumChemAgent.__new__(QuantumChemAgent)
    agent.backend = "openai"
    agent.history = []
    agent._current_calculations = []

    def fake_reply(_question: str) -> str:
        agent._record_result(mapping_example(0, "+", "parity"))
        return "Resultado obtido."

    agent._reply_openai = fake_reply
    result = agent.reply_result("Calcule")

    assert result["answer"] == "Resultado obtido."
    assert len(result["calculations"]) == 1
    assert result["calculations"][0]["calculation_badge"] == "Calculado com Ket"


def test_conceptual_reply_has_no_ket_badge_metadata():
    agent = QuantumChemAgent.__new__(QuantumChemAgent)
    agent.backend = "openai"
    agent.history = []
    agent._current_calculations = [{"stale": True}]
    agent._reply_openai = lambda _question: "Uma explicação conceitual."

    result = agent.reply_result("O que é um qubit?")

    assert result["calculations"] == []


def test_parse_mapping_request_in_portuguese():
    assert parse_mapping_request("Mapeie a criação no orbital 2 com BK") == {
        "orbital": 2,
        "action": "+",
        "mapping": "bravyi_kitaev",
    }
    assert parse_mapping_request("Calcule a aniquilação do orbital 3 por paridade") == {
        "orbital": 3,
        "action": "-",
        "mapping": "parity",
    }


def test_conceptual_mapping_question_does_not_bypass_llm():
    assert parse_mapping_request("Explique o mapeamento Jordan-Wigner") is None


def test_direct_mapping_request_skips_llm():
    agent = QuantumChemAgent.__new__(QuantumChemAgent)
    agent.backend = "openai"
    agent.history = []
    agent._current_calculations = []
    agent._reply_openai = lambda _question: (_ for _ in ()).throw(AssertionError("LLM não deveria ser chamada"))

    result = agent.reply_result("Calcule a criação no orbital 1 com Jordan-Wigner")

    assert "O Ket calculou" in result["answer"]
    assert result["calculations"][0]["mapping"] == "jordan_wigner"


def test_direct_mapping_result_is_ready_without_an_agent():
    result = direct_mapping_result("aniquilação no orbital 1 com parity")

    assert result is not None
    assert result["calculations"][0]["calculation_provider"] == "Ket"
