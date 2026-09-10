"""Conversation loop using the OpenAI Responses API and local chemistry tools."""

from __future__ import annotations

import os
from typing import Any

from .tools import TOOL_DEFINITIONS, call_tool

SYSTEM_PROMPT = """Você é um assistente didático de química quântica. Responda em português,
de forma clara e cientificamente cuidadosa. Para resultados numéricos ou mapeamentos,
use as ferramentas disponíveis em vez de inventar valores. Explique quando um cálculo
molecular requer PySCF/WSL2."""


class QuantumChemAgent:
    """A small stateful agent: messages persist for the lifetime of this object."""

    def __init__(self) -> None:
        try:
            from openai import OpenAI  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise RuntimeError("Pacote 'openai' ausente. Execute: pip install -e .") from exc
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY não configurada. Copie .env.example para .env e preencha a chave.")
        self.client = OpenAI()
        self.history: list[dict[str, Any]] = []

    def reply(self, user_text: str) -> str:
        self.history.append({"role": "user", "content": user_text})
        response = self.client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
            instructions=SYSTEM_PROMPT,
            input=self.history,
            tools=TOOL_DEFINITIONS,
        )
        while any(item.type == "function_call" for item in response.output):
            tool_outputs = []
            for item in response.output:
                if item.type == "function_call":
                    tool_outputs.append({"type": "function_call_output", "call_id": item.call_id, "output": call_tool(item.name, item.arguments)})
            response = self.client.responses.create(
                model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
                previous_response_id=response.id,
                input=tool_outputs,
                tools=TOOL_DEFINITIONS,
            )
        answer = response.output_text
        self.history.append({"role": "assistant", "content": answer})
        return answer
