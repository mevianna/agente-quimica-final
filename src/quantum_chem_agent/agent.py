"""Conversation loop using the OpenAI Responses API and local chemistry tools."""

import os
import json
import re
import unicodedata
from typing import Any

from .tools import TOOL_DEFINITIONS, call_tool, fermion_algebra, mapping_example, molecular_hamiltonian

SYSTEM_PROMPT = """Você é um assistente didático de química quântica. Responda em português,
de forma clara e cientificamente cuidadosa. Para resultados numéricos ou mapeamentos,
é obrigatório chamar uma ferramenta Ket disponível; nunca calcule ou infira o resultado
apenas no texto. Ao comparar mapeamentos, use o contexto da conversa para resolver referências
como 'o mesmo orbital' e chame a ferramenta Ket para o novo mapeamento antes de comparar.
Para construir produtos fermiônicos, calcular adjuntos, colocar operadores em ordem normal
ou verificar conservação de partículas e spin, é obrigatório chamar fermion_algebra.
Perguntas conceituais podem ser respondidas normalmente. Explique quando um cálculo
molecular requer PySCF/WSL2. Quando uma ferramenta retornar calculation_status='completed',
afirme que o resultado foi calculado pela biblioteca local Ket. Nunca alegue erro de uma
ferramenta, inconsistência ou fallback analítico se a ferramenta não retornar um campo error."""


def _plain_text(text: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFKD", text.lower())
        if not unicodedata.combining(character)
    )


_FERMION_ACTIONS = re.compile(
    r"\b(criacao|criar|crie|criador|creation|create|createfermion|"
    r"aniquilacao|aniquilar|aniquile|aniquilador|destruicao|destruir|destrua|"
    r"annihilation|annihilate|annihilatefermion)\b"
)
_CREATION_WORDS = {"criacao", "criar", "crie", "criador", "creation", "create", "createfermion"}


def _parse_fermion_factors(user_text: str) -> list[dict[str, Any]]:
    """Extract explicit natural-language factors while preserving their order."""
    text = _plain_text(user_text)
    matches = list(_FERMION_ACTIONS.finditer(text))
    factors = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        segment = text[match.start():end]
        orbital = re.search(r"\b(?:orbital|modo|indice)\s*(?:numero\s*)?[:#-]?\s*(\d+)\b", segment)
        if orbital is None:
            return []
        spin_match = re.search(r"\b(?:spin\s*)?(alfa|alpha|beta)\b", segment)
        spin = None
        if spin_match is not None:
            spin = "b" if spin_match.group(1) == "beta" else "a"
        factors.append(
            {
                "orbital": int(orbital.group(1)),
                "action": "+" if match.group(1) in _CREATION_WORDS else "-",
                "spin": spin,
            }
        )
    return factors


def parse_fermion_request(user_text: str) -> dict[str, Any] | None:
    """Recognize explicit Ket algebra requests that can bypass the LLM."""
    text = _plain_text(user_text)
    factors = _parse_fermion_factors(user_text)
    if not factors:
        return None

    if re.search(r"\b(ordem normal|ordenamento normal|normal order(?:ed)?)\b", text):
        operation = "normal_order"
    elif re.search(r"\b(adjunto|dagger|conjugado hermitiano|hermitiano conjugado)\b", text) or "†" in user_text:
        operation = "adjoint"
    elif re.search(r"\b(conserva|conservar|conservacao|verifique a conservacao)\b", text):
        operation = "conservation"
    elif len(factors) >= 2 and re.search(
        r"\b(produto|construa|construir|monte|montar|multiplique|vezes|seguida|seguido)\b", text
    ):
        operation = "product"
    else:
        return None

    request: dict[str, Any] = {
        "orbitals": [factor["orbital"] for factor in factors],
        "actions": [factor["action"] for factor in factors],
        "operation": operation,
    }
    if any(factor["spin"] is not None for factor in factors):
        request["spins"] = [
            factor["spin"] if factor["spin"] is not None else ("a" if factor["orbital"] % 2 == 0 else "b")
            for factor in factors
        ]
    return request


def parse_mapping_request(user_text: str) -> dict[str, Any] | None:
    """Recognize unambiguous mapping requests that can bypass the LLM."""
    text = _plain_text(user_text)
    creation = re.search(r"\b(criacao|criar|creation)\b", text)
    annihilation = re.search(r"\b(aniquilacao|aniquilar|annihilation)\b", text)
    orbital = re.search(r"\b(?:orbital|modo|indice)\s*(?:numero\s*)?[:#-]?\s*(\d+)\b", text)
    action_mentions = re.findall(r"\b(criacao|criar|creation|aniquilacao|aniquilar|annihilation)\b", text)
    orbital_mentions = re.findall(r"\b(?:orbital|modo|indice)\s*(?:numero\s*)?[:#-]?\s*\d+\b", text)
    if (
        (creation is None) == (annihilation is None)
        or orbital is None
        or len(action_mentions) != 1
        or len(orbital_mentions) != 1
    ):
        return None

    if re.search(r"\b(bravyi(?:[- ]kitaev)?|bk)\b", text):
        mapping = "bravyi_kitaev"
    elif re.search(r"\b(parity|paridade)\b", text):
        mapping = "parity"
    else:
        mapping = "jordan_wigner"
    return {
        "orbital": int(orbital.group(1)),
        "action": "+" if creation else "-",
        "mapping": mapping,
    }


def _format_coefficient(coefficient: dict[str, float]) -> str:
    real, imag = coefficient["real"], coefficient["imag"]
    if abs(imag) < 1e-12:
        return f"{real:g}"
    if abs(real) < 1e-12:
        return f"{imag:g}i"
    return f"({real:g} {imag:+g}i)"


def _mapping_answer(result: dict[str, Any]) -> str:
    operation = "criação" if result["action"] == "creation" else "aniquilação"
    terms = []
    for term in result["pauli_terms"]:
        paulis = " ".join(
            f"{pauli}{qubit}" for qubit, pauli in sorted(term["paulis"].items(), key=lambda item: int(item[0]))
        ) or "I"
        terms.append(f"{_format_coefficient(term['coefficient'])} · {paulis}")
    expression = " + ".join(terms).replace("+ -", "− ")
    return (
        f"O Ket calculou o operador de {operation} no orbital indicado usando o mapeamento "
        f"{result['mapping_label']}:\n\n{expression}\n\n"
        "Abra o modo de aprendizagem abaixo para reproduzir o cálculo em código."
    )


def direct_mapping_result(user_text: str) -> dict[str, Any] | None:
    """Execute a clear mapping request with Ket, without initializing an LLM."""
    request = parse_mapping_request(user_text)
    if request is None:
        return None
    result = mapping_example(**request)
    return {"answer": _mapping_answer(result), "calculations": [result]}


def _format_fermion_terms(terms: list[dict[str, Any]]) -> str:
    if not terms:
        return "0"
    formatted = [
        f"{_format_coefficient(term['coefficient'])} · {term['notation']}"
        for term in terms
    ]
    return " + ".join(formatted).replace("+ -", "− ")


def _fermion_answer(result: dict[str, Any]) -> str:
    operation = result["operation"]
    input_notation = result["input_term"]["notation"]
    if operation == "product":
        return (
            f"O Ket construiu o produto fermiônico, preservando a ordem dos fatores:\n\n"
            f"{_format_fermion_terms(result['result_terms'])}\n\n"
            "Abra o modo de aprendizagem abaixo para reproduzir a construção em código."
        )
    if operation == "adjoint":
        return (
            f"O Ket calculou o adjunto de {input_notation}:\n\n"
            f"{_format_fermion_terms(result['result_terms'])}\n\n"
            "Abra o modo de aprendizagem abaixo para ver a operação em código."
        )
    if operation == "normal_order":
        return (
            f"O Ket colocou {input_notation} em ordem normal aplicando as relações de anticomutação:\n\n"
            f"{_format_fermion_terms(result['result_terms'])}\n\n"
            "Abra o modo de aprendizagem abaixo para reproduzir o cálculo em código."
        )
    particle = "sim" if result["conserves_particle_number"] else "não"
    spin = "sim" if result["conserves_spin_z"] else "não"
    two_body = "sim" if result["is_two_body_number_conserving"] else "não"
    return (
        f"O Ket analisou o produto {input_notation}:\n\n"
        f"• Conserva o número de partículas: {particle}.\n"
        f"• Conserva a componente z do spin: {spin}.\n"
        f"• É de no máximo dois corpos e conserva partículas: {two_body}.\n\n"
        "Abra o modo de aprendizagem abaixo para ver as verificações executadas."
    )


def direct_fermion_result(user_text: str) -> dict[str, Any] | None:
    """Execute a clear fermionic algebra request with Ket, without initializing an LLM."""
    request = parse_fermion_request(user_text)
    if request is None:
        return None
    result = fermion_algebra(**request)
    return {"answer": _fermion_answer(result), "calculations": [result]}


def direct_calculation_result(user_text: str) -> dict[str, Any] | None:
    """Try every deterministic request understood without an LLM."""
    return direct_fermion_result(user_text) or direct_mapping_result(user_text)


class QuantumChemAgent:
    """A small stateful agent: messages persist for the lifetime of this object."""

    def __init__(self) -> None:
        self.backend = os.getenv("LLM_BACKEND", "gemini").lower()
        self.history: list[dict[str, Any]] = []
        self._current_calculations: list[dict[str, Any]] = []
        self._pending_gemini_context: list[dict[str, Any]] = []
        if self.backend == "gemini":
            self._init_gemini()
        elif self.backend == "ollama":
            self._init_ollama()
        elif self.backend == "openai":
            self._init_openai()
        else:
            raise RuntimeError("LLM_BACKEND deve ser 'gemini', 'ollama' ou 'openai'.")

    def _init_gemini(self) -> None:
        try:
            from google import genai  # pylint: disable=import-outside-toplevel
            from google.genai import types  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise RuntimeError("Pacote 'google-genai' ausente. Execute: pip install -e .") from exc
        if not os.getenv("GEMINI_API_KEY"):
            raise RuntimeError("GEMINI_API_KEY não configurada. Crie uma chave no Google AI Studio e preencha .env.")
        self.client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

        def ket_mapping_example(orbital: int, action: str, mapping: str = "jordan_wigner") -> dict[str, Any]:
            """Mapeia criação/aniquilação com Jordan-Wigner, Parity ou Bravyi-Kitaev usando Ket."""
            return self._record_result(mapping_example(orbital, action, mapping))

        def ket_molecular_hamiltonian(
            symbols: list[str],
            coordinates: list[list[float]],
            basis: str = "sto-3g",
            mapping: str = "jordan_wigner",
        ) -> dict[str, Any]:
            """Calcula e mapeia um Hamiltoniano molecular usando Ket (requer PySCF)."""
            return self._record_result(molecular_hamiltonian(symbols, coordinates, basis, mapping))

        def ket_fermion_algebra(
            orbitals: list[int],
            actions: list[str],
            operation: str,
            spins: list[str] | None = None,
        ) -> dict[str, Any]:
            """Executa produto, adjunto, ordem normal ou conservação fermiônica usando Ket."""
            return self._record_result(fermion_algebra(orbitals, actions, operation, spins))

        # Keep closures alive for the lifetime of the Gemini chat.
        self._gemini_tools = [ket_mapping_example, ket_fermion_algebra, ket_molecular_hamiltonian]
        self.chat = self.client.chats.create(
            model=os.getenv("GEMINI_MODEL", "gemini-3.6-flash"),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=self._gemini_tools,
            ),
        )

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
        self.client = Client(timeout=float(os.getenv("OLLAMA_TIMEOUT", "45")))

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
                    tool_outputs.append(
                        {"type": "function_call_output", "call_id": item.call_id, "output": self._call_and_record(item.name, item.arguments)}
                    )
            response = self.client.responses.create(
                model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
                previous_response_id=response.id,
                input=tool_outputs,
                tools=TOOL_DEFINITIONS,
            )
        answer = response.output_text
        self.history.append({"role": "assistant", "content": answer})
        return answer

    def _reply_gemini(self, user_text: str) -> str:
        """Use Gemini with automatic execution of the local chemistry functions."""
        pending_context = getattr(self, "_pending_gemini_context", [])
        message = user_text
        if pending_context:
            context = json.dumps(pending_context[-4:], ensure_ascii=False)
            message = (
                "Contexto confiável de interações anteriores, incluindo resultados realmente "
                f"calculados pelo Ket:\n{context}\n\nNova mensagem do usuário:\n{user_text}"
            )
        try:
            response = self.chat.send_message(message)
        except Exception as exc:
            raise RuntimeError(f"Não foi possível consultar Gemini. Verifique a chave e a conexão. Detalhe: {exc}") from exc
        pending_context.clear()
        answer = response.text
        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": answer})
        return answer

    def _reply_ollama(self, user_text: str) -> str:
        """Use Ollama's local chat endpoint, including local tool calls."""
        self.history.append({"role": "user", "content": user_text})
        history_limit = max(2, int(os.getenv("OLLAMA_HISTORY_MESSAGES", "10")))
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, *self.history[-history_limit:]]
        model = os.getenv("OLLAMA_MODEL", "qwen3:4b")
        try:
            response = self.client.chat(
                model=model,
                messages=messages,
                tools=[mapping_example, fermion_algebra, molecular_hamiltonian],
                think=False,
                keep_alive=os.getenv("OLLAMA_KEEP_ALIVE", "15m"),
                options={
                    "temperature": float(os.getenv("OLLAMA_TEMPERATURE", "0.2")),
                    "num_predict": int(os.getenv("OLLAMA_NUM_PREDICT", "500")),
                },
            )
        except Exception as exc:
            raise RuntimeError(
                f"Não foi possível conectar ao Ollama. Instale-o e execute 'ollama pull {model}'. Detalhe: {exc}"
            ) from exc
        while response.message.tool_calls or []:
            messages.append(response.message)
            for tool_call in response.message.tool_calls:
                function = tool_call.function
                result = self._call_and_record(function.name, json.dumps(function.arguments))
                messages.append({"role": "tool", "tool_name": function.name, "content": result})
            response = self.client.chat(
                model=model,
                messages=messages,
                tools=[mapping_example, fermion_algebra, molecular_hamiltonian],
                think=False,
                keep_alive=os.getenv("OLLAMA_KEEP_ALIVE", "15m"),
                options={"temperature": 0.2, "num_predict": int(os.getenv("OLLAMA_NUM_PREDICT", "500"))},
            )
        answer = response.message.content
        self.history.append({"role": "assistant", "content": answer})
        self.history = self.history[-history_limit:]
        return answer

    def _record_result(self, result: dict[str, Any]) -> dict[str, Any]:
        """Record only successful Ket executions for trustworthy UI provenance."""
        if result.get("calculation_status") == "completed" and result.get("calculation_provider") == "Ket":
            self._current_calculations.append(result)
        return result

    def _call_and_record(self, name: str, arguments: str) -> str:
        serialized = call_tool(name, arguments)
        result = json.loads(serialized)
        self._record_result(result)
        return serialized

    def remember_direct_exchange(self, user_text: str, result: dict[str, Any]) -> None:
        """Preserve a deterministic Ket exchange as conversational context."""
        answer = result["answer"]
        calculations = []
        for calculation in result.get("calculations", []):
            calculations.append(
                {
                    key: calculation[key]
                    for key in (
                        "calculation_type",
                        "input",
                        "input_term",
                        "action",
                        "actions",
                        "operation",
                        "orbitals",
                        "spins",
                        "mapping",
                        "mapping_label",
                        "qubits_required",
                        "pauli_terms",
                        "result_terms",
                        "conserves_particle_number",
                        "conserves_spin_z",
                        "is_two_body_number_conserving",
                    )
                    if key in calculation
                }
            )
        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": answer})
        pending_context = getattr(self, "_pending_gemini_context", None)
        if pending_context is None:
            pending_context = []
            self._pending_gemini_context = pending_context
        pending_context.append(
            {
                "user_request": user_text,
                "ket_calculations": calculations,
                "assistant_answer": answer,
            }
        )
        del pending_context[:-4]

    def reply_result(self, user_text: str) -> dict[str, Any]:
        """Return answer text plus provenance for calculations actually run in this turn."""
        self._current_calculations = []
        direct_result = direct_calculation_result(user_text)
        if direct_result is not None:
            self._current_calculations.extend(direct_result["calculations"])
            self.remember_direct_exchange(user_text, direct_result)
            return direct_result
        if self.backend == "gemini":
            answer = self._reply_gemini(user_text)
        else:
            answer = self._reply_ollama(user_text) if self.backend == "ollama" else self._reply_openai(user_text)
        return {"answer": answer, "calculations": list(self._current_calculations)}

    def reply(self, user_text: str) -> str:
        """Backward-compatible text-only response used by the terminal client."""
        return self.reply_result(user_text)["answer"]
