# Quantum Chemistry Agent

Agente de linha de comando que conversa em linguagem natural e usa as rotinas de química quântica implementadas no projeto Ket. A primeira versão não tem interface gráfica: ela mantém o contexto da conversa, usa um modelo LLM local e disponibiliza ferramentas para consultar mapeamentos fermiônico→qubit e construir Hamiltonianos moleculares.

## Estrutura

- `src/quantum_chem_agent/`: agente, memória da conversa e ferramentas científicas.
- `ket/`: cópia do projeto Ket usada como biblioteca local. Seu código mantém a licença Apache-2.0 e os créditos originais.
- `tests/`: testes do agente.

## Requisitos

- Python 3.10 ou superior.
- Por padrão: [Ollama](https://ollama.com/download) instalado e o modelo local `qwen3:4b` baixado. Não exige chave nem créditos.
- Alternativamente: uma chave da API da OpenAI.
- Para gerar Hamiltonianos a partir de uma molécula: PySCF em ambiente Linux/WSL2. O PySCF não possui suporte nativo para Windows.

## Instalação no Windows (modo inicial)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
```

Baixe o Ollama para Windows e, em um novo Prompt de Comando, execute:

```bat
ollama pull qwen3:4b
```

O arquivo `.env` já seleciona essa opção local. Nunca publique `.env`, especialmente se você decidir acrescentar uma chave OpenAI.

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

Para usar OpenAI no lugar do Ollama, ajuste `.env` para `LLM_BACKEND=openai` e preencha `OPENAI_API_KEY`.

## PySCF no WSL2

No Ubuntu/WSL2, instale as dependências químicas e execute o mesmo projeto:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[chemistry,dev]'
```

Assim, o agente poderá gerar Hamiltonianos moleculares via Hartree-Fock e mapeá-los para operadores de Pauli.
