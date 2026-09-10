# Quantum Chemistry Agent

Agente de linha de comando que conversa em linguagem natural e usa as rotinas de química quântica implementadas no projeto Ket. A primeira versão não tem interface gráfica: ela mantém o contexto da conversa, usa um modelo LLM e disponibiliza ferramentas para consultar mapeamentos fermiônico→qubit e construir Hamiltonianos moleculares.

## Estrutura

- `src/quantum_chem_agent/`: agente, memória da conversa e ferramentas científicas.
- `ket/`: cópia do projeto Ket usada como biblioteca local. Seu código mantém a licença Apache-2.0 e os créditos originais.
- `tests/`: testes do agente.

## Requisitos

- Python 3.10 ou superior.
- Por padrão: uma chave gratuita do [Google AI Studio](https://aistudio.google.com/app/apikey) para Gemini API.
- Alternativamente: [Ollama](https://ollama.com/download) instalado e o modelo local `qwen3:4b` baixado. Não exige chave, mas requer espaço em disco.
- Alternativamente: uma chave da API da OpenAI.
- Para gerar Hamiltonianos a partir de uma molécula: PySCF em ambiente Linux/WSL2. O PySCF não possui suporte nativo para Windows.

## Instalação no Windows (modo inicial)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
```

Crie uma chave no Google AI Studio e edite `.env`:

```text
GEMINI_API_KEY=sua_chave_aqui
```

O Gemini 3.6 Flash oferece chamadas de função e está disponível na camada gratuita com limites de uso. Nunca publique `.env`.

## Executar

O modo demonstração funciona localmente e não consome API:

```powershell
python -m quantum_chem_agent --demo
```

Para conversar com o agente:

```powershell
python -m quantum_chem_agent
```

Digite `sair` para encerrar. O agente mantém as mensagens anteriores durante a sessão.

Para usar Ollama, ajuste `.env` para `LLM_BACKEND=ollama`, instale o Ollama e execute `ollama pull qwen3:4b`. Para OpenAI, ajuste para `LLM_BACKEND=openai` e preencha `OPENAI_API_KEY`.

## PySCF no WSL2

No Ubuntu/WSL2, instale as dependências químicas e execute o mesmo projeto:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[chemistry,dev]'
```

Assim, o agente poderá gerar Hamiltonianos moleculares via Hartree-Fock e mapeá-los para operadores de Pauli.
