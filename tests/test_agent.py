"""Tests for structured calculation provenance without contacting an LLM."""

import inspect

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
    assert agent.history[0]["content"] == "Calcule a criação no orbital 1 com Jordan-Wigner"
    assert agent._pending_gemini_context[0]["ket_calculations"][0]["input"] == "a_1†"


def test_direct_mapping_result_is_ready_without_an_agent():
    result = direct_mapping_result("aniquilação no orbital 1 com parity")

    assert result is not None
    assert result["calculations"][0]["calculation_provider"] == "Ket"


def test_gemini_receives_direct_ket_exchange_as_context():
    class FakeResponse:
        text = "Comparação concluída."

    class FakeChat:
        def __init__(self):
            self.message = ""

        def send_message(self, message: str):
            self.message = message
            return FakeResponse()

    agent = QuantumChemAgent.__new__(QuantumChemAgent)
    agent.backend = "gemini"
    agent.history = []
    agent._current_calculations = []
    agent._pending_gemini_context = []
    agent.chat = FakeChat()

    first = direct_mapping_result("Mapeie a criação no orbital 2 com Jordan-Wigner")
    assert first is not None
    agent.remember_direct_exchange("Mapeie a criação no orbital 2 com Jordan-Wigner", first)
    answer = agent._reply_gemini("Compare com Bravyi-Kitaev para o mesmo orbital")

    assert answer == "Comparação concluída."
    assert '"input": "a_2†"' in agent.chat.message
    assert '"mapping": "jordan_wigner"' in agent.chat.message
    assert "mesmo orbital" in agent.chat.message
    assert agent._pending_gemini_context == []


def test_gemini_tool_uses_runtime_annotations(monkeypatch):
    """The Gemini SDK needs actual types when validating automatic tool calls."""
    monkeypatch.setenv("LLM_BACKEND", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "validation-only-not-sent")

    agent = QuantumChemAgent()
    signature = inspect.signature(agent._gemini_tools[0])

    assert signature.parameters["orbital"].annotation is int
    assert signature.parameters["action"].annotation is str
    assert signature.parameters["mapping"].annotation is str
