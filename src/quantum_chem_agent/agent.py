"""Conversation loop using the OpenAI Responses API and local chemistry tools."""

from __future__ import annotations

import os
import json
from typing import Any

from .tools import TOOL_DEFINITIONS, call_tool, mapping_example, molecular_hamiltonian

SYSTEM_PROMPT = """Você é um assistente didático de química quântica. Responda em português,
de forma clara e cientificamente cuidadosa. Para resultados numéricos ou mapeamentos,
use as ferramentas disponíveis em vez de inventar valores. Explique quando um cálculo
molecular requer PySCF/WSL2."""


class QuantumChemAgent:
    """A small stateful agent: messages persist for the lifetime of this object."""

    def __init__(self) -> None:
        self.backend = os.getenv("LLM_BACKEND", "ollama").lower()
        self.history: list[dict[str, Any]] = []
        if self.backend == "ollama":
            self._init_ollama()
        elif self.backend == "openai":
            self._init_openai()
        else:
            raise RuntimeError("LLM_BACKEND deve ser 'ollama' ou 'openai'.")

    def _init_openai(self) -> None:
        try:
            from openai import OpenAI  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise RuntimeError("Pacote 'openai' ausente. Execute: pip install -e .") from exc
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY não configurada. Copie .env.example para .env e preencha a chave.")
        self.client = OpenAI()

    def _init_ollama(self) -> None:
        try:
            from ollama import Client  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise RuntimeError("Pacote 'ollama' ausente. Execute: pip install -e .") from exc
        self.client = Client()

    def _reply_openai(self, user_text: str) -> str:
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

    def _reply_ollama(self, user_text: str) -> str:
        """Use Ollama's local chat endpoint, including local tool calls."""
        self.history.append({"role": "user", "content": user_text})
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, *self.history]
        model = os.getenv("OLLAMA_MODEL", "qwen3:4b")
        try:
            response = self.client.chat(model=model, messages=messages, tools=[mapping_example, molecular_hamiltonian])
        except Exception as exc:
            raise RuntimeError(
                f"Não foi possível conectar ao Ollama. Instale-o e execute 'ollama pull {model}'. Detalhe: {exc}"
            ) from exc
        while response.message.tool_calls or []:
            messages.append(response.message)
            for tool_call in response.message.tool_calls:
                function = tool_call.function
                result = call_tool(function.name, json.dumps(function.arguments))
                messages.append({"role": "tool", "tool_name": function.name, "content": result})
            response = self.client.chat(model=model, messages=messages, tools=[mapping_example, molecular_hamiltonian])
        answer = response.message.content
        self.history.append({"role": "assistant", "content": answer})
        return answer

    def reply(self, user_text: str) -> str:
        return self._reply_ollama(user_text) if self.backend == "ollama" else self._reply_openai(user_text)
