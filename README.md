# Agente Inteligente de Química Quântica

Assistente educacional que recebe perguntas em linguagem natural, mantém o contexto da conversa e utiliza ferramentas científicas para apoiar o estudo de química quântica.

O projeto combina um modelo de linguagem (LLM) com a biblioteca Ket. A LLM interpreta as perguntas, explica conceitos e conduz a conversa. Quando o usuário solicita um cálculo compatível, o agente utiliza o Ket para obter um resultado determinístico e o identifica na interface com o selo **Calculado com Ket**.

## Funcionalidades

- entrada de texto em uma interface web;
- respostas em linguagem natural geradas por uma LLM;
- memória básica durante a sessão da conversa;
- integração com o Ket para cálculos e mapeamentos quânticos;
- mapeamentos Jordan–Wigner, Parity e Bravyi–Kitaev;
- tratamento de erros de configuração, conexão e entrada;
- indicação da origem dos cálculos e exemplos de código reproduzível.

## Tecnologias utilizadas

- **Python 3.10 ou superior**;
- **Google Gemini** como LLM recomendada;
- **OpenAI API** ou **Ollama** como alternativas;
- **Ket** para programação e cálculos quânticos;
- **HTML, CSS e JavaScript** na interface web;
- **pytest** nos testes automatizados.

## Estrutura do projeto

```text
src/quantum_chem_agent/  agente, memória e ferramentas
web/                     interface web e servidor local
tests/                   testes automatizados
ket/                     cópia do código-fonte do Ket
.env.example             exemplo de configuração
pyproject.toml           dependências e configuração do projeto
```

## O que é necessário

Antes de começar, instale:

1. [Python](https://www.python.org/downloads/) 3.10 ou superior;
2. [Git](https://git-scm.com/download/win), caso queira clonar o repositório;
3. um navegador, como Chrome, Edge ou Firefox;
4. uma chave da API do Gemini criada no [Google AI Studio](https://aistudio.google.com/app/apikey).

Durante a instalação do Python no Windows, marque a opção **Add Python to PATH**.

## Instalação no Windows

### 1. Baixe o projeto

No PowerShell:

```powershell
git clone https://github.com/mevianna/agente-quimica-final.git
cd agente-quimica-final
```

Também é possível baixar o ZIP pelo botão **Code > Download ZIP** do GitHub. Nesse caso, extraia o arquivo e abra o PowerShell dentro da pasta extraída. Os próximos comandos devem ser executados na pasta que contém `pyproject.toml`.

### 2. Crie um ambiente virtual

```powershell
py -m venv .venv
```

### 3. Instale as dependências

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
```

Os comandos utilizam diretamente o Python do ambiente virtual. Não é necessário ativar o ambiente nem modificar a política de execução do PowerShell.

### 4. Configure a LLM

Crie o arquivo de configuração local:

```powershell
Copy-Item .env.example .env
```

Abra o arquivo `.env` em um editor de texto e preencha a chave do Gemini:

```text
LLM_BACKEND=gemini
GEMINI_API_KEY=cole_sua_chave_aqui
GEMINI_MODEL=gemini-3.6-flash
```

Não coloque aspas ao redor da chave. O arquivo `.env` é ignorado pelo Git e não deve ser publicado.

### 5. Inicie a interface web

```powershell
.\.venv\Scripts\python.exe web\server.py
```

Quando aparecer a mensagem `Chat disponível em http://127.0.0.1:8000`, abra este endereço no navegador:

<http://127.0.0.1:8000>

Para encerrar o servidor, volte ao PowerShell e pressione `Ctrl+C`.

## Sobre a instalação do Ket

O código Python do Ket já está na pasta `ket/`, portanto não é necessário executar `pip install ket-lang` para iniciar a interface ou fazer perguntas conceituais à LLM.

Os cálculos locais do Ket também dependem dos arquivos nativos `ket.dll` e `kbw.dll`, esperados em:

```text
ket/src/ket/clib/libs/
```

Se esses dois arquivos estiverem presentes na cópia recebida, nenhuma instalação adicional do Ket é necessária. Se estiverem ausentes, a interface e as respostas conceituais da LLM ainda poderão funcionar, mas os cálculos marcados como **Calculado com Ket** não funcionarão. A versão atual do projeto usa uma edição do Ket com recursos de química que não devem ser substituídos automaticamente pela versão comum do `ket-lang`.

## Solução de problemas

### O comando `py` não foi encontrado

Instale o Python 3.10 ou superior e marque **Add Python to PATH**. Se o computador reconhecer `python`, mas não `py`, use este comando na etapa de criação do ambiente:

```powershell
python -m venv .venv
```

### Erro ao criar o ambiente virtual

Confirme que o PowerShell está aberto na pasta que contém `pyproject.toml` e que o Python foi instalado corretamente.

### Erro de chave do Gemini

Confirme que:

- o arquivo se chama exatamente `.env`;
- ele está na raiz do projeto, ao lado de `pyproject.toml`;
- `LLM_BACKEND` está definido como `gemini`;
- `GEMINI_API_KEY` contém uma chave válida, sem aspas;
- o computador está conectado à internet.

Uma chave do ChatGPT/OpenAI não funciona no Gemini.

### O navegador não abriu automaticamente

Isso é normal. Abra manualmente <http://127.0.0.1:8000> depois que o servidor informar que está disponível.

### A porta 8000 já está em uso

Encerre outro programa que esteja utilizando a porta 8000 e execute o servidor novamente.

### Erro mencionando `ket.dll`, `kbw.dll` ou Ket

Confira se os arquivos `ket.dll` e `kbw.dll` estão em `ket/src/ket/clib/libs/`. Esse erro não é causado pela chave da LLM; ele indica que os componentes nativos do Ket não estão presentes na cópia do projeto.

## Observações

- A memória existe somente durante a sessão e não é salva em banco de dados.
- O servidor web é local e foi criado para demonstração acadêmica.
- É necessário acesso à internet para instalar as dependências e usar Gemini ou OpenAI.
- A pasta `ket/` mantém a licença Apache-2.0 e os créditos dos autores originais.
