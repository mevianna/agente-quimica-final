# Agente Inteligente de Química Quântica

Assistente educacional com interface web que recebe perguntas em linguagem natural e utiliza ferramentas científicas para apoiar o estudo de química quântica.

O projeto combina um modelo de linguagem (LLM) com a biblioteca Ket. A LLM interpreta perguntas e explica conceitos. Quando o usuário solicita um cálculo compatível, o agente usa o Ket localmente e identifica o resultado com o selo **Calculado com Ket**.

## Funcionalidades

- interface web executada no próprio computador;
- respostas em português geradas por uma LLM;
- memória durante a sessão;
- cálculos e mapeamentos com o Ket;
- mapeamentos Jordan–Wigner, Parity e Bravyi–Kitaev;
- produto fermiônico, adjunto, ordem normal e verificações de conservação;
- indicação da origem dos cálculos e exemplos reproduzíveis.

## Tecnologias utilizadas

- **Python 3.12** para a aplicação e a integração dos componentes;
- **Google Gemini** como modelo de linguagem recomendado;
- **OpenAI API** e **Ollama** como alternativas de modelo de linguagem;
- **Ket** para programação e cálculos quânticos;
- **HTML, CSS e JavaScript** para a interface web;
- **PowerShell** para os comandos de instalação e execução no Windows;
- **pytest** para os testes automatizados.

## Antes de começar

Este guia foi preparado para **Windows 10 ou 11 de 64 bits**. Não é necessário conhecer o Ket nem ter o VS Code instalado.

Será necessário:

1. **Python 3.12 de 64 bits**, versão testada com o projeto, disponível em [python.org](https://www.python.org/downloads/);
2. **Git**, apenas para quem preferir clonar o projeto, disponível em [git-scm.com](https://git-scm.com/download/win);
3. um navegador, como Chrome, Edge ou Firefox;
4. uma chave da API do Gemini, criada no [Google AI Studio](https://aistudio.google.com/app/apikey);
5. os binários `ket.dll` e `kbw.dll`, já incluídos neste repositório, para executar cálculos locais. Consulte [Arquivos necessários para o Ket](#arquivos-necessários-para-o-ket).

Ao instalar o Python, marque **Add Python to PATH** e mantenha o Python Launcher selecionado.

> Execute os comandos abaixo no PowerShell e sempre dentro da pasta do projeto.

## Instalação no Windows

### 1. Obtenha o projeto

Com Git:

```powershell
git clone https://github.com/mevianna/agente-quimica-final.git
cd agente-quimica-final
```

Sem Git, use **Code > Download ZIP** na página do GitHub, extraia todo o ZIP, abra a pasta extraída e selecione **Abrir no Terminal**.

Antes de continuar, confirme que a pasta contém `README.md` e `pyproject.toml`, além de `src`, `web` e `ket`.

### 2. Confirme o Python

```powershell
py -3.12 --version
```

O resultado deve começar com `Python 3.12`. Se `py` não for reconhecido, consulte a solução de problemas.

### 3. Crie o ambiente isolado

```powershell
py -3.12 -m venv .venv
```

Isso cria um Python exclusivo para o projeto e evita o uso acidental de Anaconda ou de outra instalação.

### 4. Instale as dependências

Com o computador conectado à internet, execute:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
```

Espere cada comando terminar. Não é necessário ativar o ambiente virtual nem alterar a política de execução do PowerShell: os comandos chamam diretamente o Python da pasta `.venv`.

Verifique a instalação. O resultado deve mostrar `Name: quantum-chem-agent`:

```powershell
.\.venv\Scripts\python.exe -m pip show quantum-chem-agent
```

### 5. Configure o Gemini

Crie a configuração local e abra-a no Bloco de Notas:

```powershell
Copy-Item .env.example .env
notepad .env
```

Encontre `GEMINI_API_KEY=` e cole sua chave depois do sinal de igual:

```text
GEMINI_API_KEY=cole_sua_chave_aqui
```

Não use espaços nem aspas. Mantenha `LLM_BACKEND=gemini` e as outras linhas como vieram no arquivo. Salve e feche o Bloco de Notas.

O `.env` contém informação secreta, é ignorado pelo Git e **não deve ser publicado nem compartilhado**.

### 6. Teste o Ket

Confirme que estes dois arquivos existem:

```text
ket\src\ket\clib\libs\ket.dll
ket\src\ket\clib\libs\kbw.dll
```

Depois execute:

```powershell
.\.venv\Scripts\python.exe -m quantum_chem_agent --demo
```

Esse teste não usa a chave da API nem a internet. Ele foi bem-sucedido se o resultado contiver:

```text
calculation_status ... completed
calculation_provider ... Ket
```

Se os arquivos não existirem ou o teste falhar mencionando DLL ou Ket, consulte [Arquivos necessários para o Ket](#arquivos-necessários-para-o-ket).

### 7. Inicie a interface

```powershell
.\.venv\Scripts\python.exe web\server.py
```

Quando aparecer `Chat disponível em http://127.0.0.1:8000`, mantenha o PowerShell aberto e acesse:

<http://127.0.0.1:8000>

Não abra `web\index.html` diretamente: a página precisa do servidor iniciado pelo comando acima.

Faça dois testes:

1. `Mapeie o operador de criação no orbital 1 usando Jordan-Wigner.`
   Deve aparecer o selo **Calculado com Ket**.
2. `Explique de forma simples o que é um qubit.`
   Essa pergunta verifica a conexão com o Gemini.

Para encerrar, volte ao PowerShell e pressione `Ctrl+C`.

## Arquivos necessários para o Ket

O código Python do Ket está na pasta `ket`, e os binários nativos para Windows de 64 bits `ket.dll` e `kbw.dll` **já fazem parte deste repositório**. Eles são necessários para o teste `--demo` e para os cálculos identificados como **Calculado com Ket**.

Ao clonar o repositório ou usar **Code > Download ZIP**, confirme que os arquivos estão exatamente em:

```text
ket\src\ket\clib\libs\
```

Não é necessário baixar essas DLLs separadamente. Se elas estiverem ausentes, obtenha novamente uma cópia completa deste repositório e repita o teste da etapa 6. Não baixe DLLs de sites desconhecidos e não execute `pip install ket-lang` para tentar substituí-las: o projeto utiliza uma cópia específica do Ket.

Sem as DLLs, o servidor e as respostas conceituais da LLM ainda podem funcionar, mas os cálculos locais do Ket não estarão disponíveis.

## Perguntas executadas diretamente pelo Ket

A integração deste projeto com a versão local do Ket possui rotas determinísticas para operações fermiônicas e mapeamentos. Nos exemplos abaixo, o agente reconhece a solicitação e executa o cálculo diretamente no Ket, sem depender da LLM para produzir o resultado. A interface identifica essas respostas com o selo **Calculado com Ket**.

### 1. Produto de operadores

> Construa o produto: criação no orbital 0 seguida de aniquilação no orbital 1.

Rota utilizada: `fermion_product`.

Outra formulação aceita:

> Multiplique criação no orbital 2 vezes aniquilação no orbital 3.

### 2. Adjunto

> Calcule o adjunto da criação no orbital 0 seguida de aniquilação no orbital 1.

Rota utilizada: `fermion_adjoint`. O Ket troca criação por aniquilação e vice-versa, além de inverter a ordem dos fatores.

### 3. Ordem normal

> Coloque em ordem normal a aniquilação no orbital 0 seguida de criação no orbital 0.

Rota utilizada: `fermion_normal_order`. Nessa operação, o Ket aplica as relações de anticomutação em vez de apenas preservar ou inverter a sequência.

### 4. Conservação

> Verifique se criação no orbital 0 e aniquilação no orbital 1 conserva partículas e spin.

Rota utilizada: `fermion_conservation`. O resultado informa separadamente:

- se o operador conserva o número de partículas;
- se conserva a componente z do spin;
- se é um operador de até dois corpos com conservação de partículas.

### 5. Jordan–Wigner

> Mapeie a criação no orbital 3 com Jordan-Wigner.

Rota utilizada: `fermion_mapping`, com o mapeamento `jordan_wigner`.

### 6. Parity

> Mapeie a aniquilação no orbital 3 por paridade.

Rota utilizada: `fermion_mapping`, com o mapeamento `parity`.

### 7. Bravyi–Kitaev

> Mapeie a criação no orbital 2 com Bravyi-Kitaev.

Rota utilizada: `fermion_mapping`, com o mapeamento `bravyi_kitaev`.

### 8. Spins explícitos

> Construa o produto: criação spin alfa no orbital 0 seguida de aniquilação spin beta no orbital 1.

Rota utilizada: `fermion_product`, com os spins alfa e beta fornecidos explicitamente.

## Como executar novamente

Nas próximas vezes, abra o PowerShell na pasta que contém `pyproject.toml` e execute:

```powershell
.\.venv\Scripts\python.exe web\server.py
```

Não é necessário repetir a instalação nem recriar `.env`.

## Solução de problemas

### O comando `py` não foi encontrado

Feche e abra o PowerShell depois de instalar o Python. Se `python --version` mostrar Python 3.12, use:

```powershell
python -m venv .venv
```

Nos passos seguintes, continue usando `.\.venv\Scripts\python.exe`.

### O projeto está usando outro Python

Crie `.venv` com `py -3.12 -m venv .venv` e use os comandos exatamente como aparecem neste guia. O caminho explícito `.\.venv\Scripts\python.exe` impede que Anaconda ou outro Python seja escolhido.

### O PowerShell não está na pasta correta

```powershell
Get-ChildItem pyproject.toml
```

Se o arquivo não for encontrado, entre na pasta extraída ou clonada antes de continuar.

### Falha em `pip install`

Confirme a conexão com a internet e a presença de `pyproject.toml`. Redes institucionais podem bloquear o `pip`; nesse caso, use outra conexão autorizada pela instituição.

### Erro de chave, modelo ou acesso ao Gemini

Confirme que:

- o arquivo se chama `.env`, e não `.env.txt`;
- ele está ao lado de `pyproject.toml`;
- `LLM_BACKEND=gemini` permanece no arquivo;
- `GEMINI_API_KEY` contém uma chave válida, sem espaços ou aspas;
- o computador está conectado à internet.

Uma chave do ChatGPT/OpenAI não funciona no Gemini. Se o erro mencionar um modelo indisponível, escolha no Google AI Studio um modelo Gemini compatível com geração de texto e atualize apenas `GEMINI_MODEL` no `.env`.

### Erro mencionando `ket.dll`, `kbw.dll` ou Ket

Confira se ambos estão em `ket\src\ket\clib\libs\` e se são as versões de 64 bits fornecidas para o projeto. Depois repita:

```powershell
.\.venv\Scripts\python.exe -m quantum_chem_agent --demo
```

Esse erro não é causado pela chave do Gemini.

### A porta 8000 já está em uso

Feche outra janela que esteja executando o servidor. Se necessário, reinicie o computador e tente novamente.

### O navegador não abriu automaticamente

Isso é normal. Com o servidor aberto no PowerShell, acesse manualmente <http://127.0.0.1:8000>.

## Estrutura do projeto

```text
src/quantum_chem_agent/  agente, memória e ferramentas
web/                     interface web e servidor local
tests/                   testes automatizados
ket/                     cópia do código-fonte do Ket
.env.example             modelo de configuração local
pyproject.toml           dependências e configuração do projeto
```

## Observações

- A memória existe somente durante a sessão e não é salva em banco de dados.
- O servidor aceita conexões apenas do próprio computador (`127.0.0.1`).
- É necessário acesso à internet para instalar dependências e usar Gemini ou OpenAI.
- A pasta `ket` mantém a licença Apache-2.0 e os créditos dos autores originais.
