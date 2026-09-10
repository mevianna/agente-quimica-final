# Roteiro de Apresentação: Validação Cruzada de Coeficientes (Ket vs OpenFermion)

Este roteiro foi estruturado em **ordem lógica de execução** (do objetivo inicial até a análise dos resultados) para guiar sua explicação em reuniões ou defesas de forma clara, técnica e natural.

---

## 1. Visão Geral e Objetivo do Script (`comparar_coeficientes_artigo.py`)
> **Como falar:**  
> *"Para validar com rigor científico o nosso módulo de química quântica (`ket.chem`), nós realizamos uma validação cruzada contra a biblioteca padrão da literatura, o **OpenFermion** (do Google). O objetivo desse script é gerar o Hamiltoniano molecular em qubits para quatro moléculas de teste ($\text{H}_2, \text{LiH}, \text{BeH}_2, \text{H}_2\text{O}$), alinhar termo a termo os operadores de Pauli e medir a precisão numérica entre as duas implementações."*

---

## 2. Passo a Passo do Fluxo de Execução

### Passo 1: Definição dos Parâmetros Químicos (`main()`)
- **O que faz:** Define as geometrias moleculares (coordenadas 3D dos átomos) e a base de funções de onda ($\text{STO-3G}$).
- **Moléculas escolhidas:** Abrangem de sistemas simples (4 qubits) a sistemas maiores com mais de 1000 termos ($\text{H}_2\text{O}$, 14 qubits).

### Passo 2: Construção do Hamiltoniano via Ket (`analisar_molecula()`)
1. Chama `ket.chem.fermionic_hamiltonian(symbols, coords, basis)`:
   - Integra-se ao **PySCF** para calcular as integrais moleculares de 1 corpo ($h_{pq}$) e 2 corpos ($h_{pqrs}$) via Hartree-Fock Restrito (RHF).
   - Monta a expressão fermiônica em segunda quantização:  
     $$H = E_{\text{nuc}} + \sum_{pq} h_{pq} a_p^\dagger a_q + \frac{1}{2}\sum_{pqrs} h_{pqrs} a_p^\dagger a_q^\dagger a_s a_r$$
2. Aplica o mapeamento **Jordan-Wigner** do Ket (`ket_jw`):
   - Converte os operadores de criação/aniquilação em operadores de Pauli ($X, Y, Z, I$) em registradores de qubits.
3. Converte para uma estrutura de dicionário canônica (`ket_hamiltonian_to_dict`):
   - Cada termo vira uma chave única (ex: `"Z0 Z1"` ou `"X3 Z4 X5"`) associada ao seu coeficiente escalar.

### Passo 3: Construção do Hamiltoniano via OpenFermion (Referência)
- Em paralelo, o script executa o pipeline canônico do OpenFermion:
  1. Cria o `MolecularData` e executa o SCF via `openfermionpyscf`.
  2. Extrai o operador fermiônico de interação (`get_fermion_operator`).
  3. Aplica a transformação de Jordan-Wigner nativa do OpenFermion (`of_jw`).
  4. Padroniza no mesmo formato de dicionário (`openfermion_hamiltonian_to_dict`).

### Passo 4: Verificação de Hermiticidade e Consistência Física
- Garante que a parte imaginária de todos os coeficientes em ambas as bibliotecas seja nula (dentro da precisão numérica $< 10^{-12}$), confirmando que os operadores gerados são observáveis físicos hermitianos ($H = H^\dagger$).

### Passo 5: Comparação Termo a Termo e Estatísticas
1. **União de Termos:** Coleta todos os termos de Pauli gerados por ambos os métodos e confere a contagem total (ex: exatamente 15 no $\text{H}_2$, 631 no $\text{LiH}$, 666 no $\text{BeH}_2$ e 1086 na $\text{H}_2\text{O}$).
2. **Divergência Termo a Termo ($\Delta_k$):**  
   $$\Delta_k = \left| c_k^{(\text{Ket})} - c_k^{(\text{OpenFermion})} \right|$$
3. **Divergência Máxima ($\Delta_{\max}$):**  
   $$\Delta_{\max} = \max_k \Delta_k$$
4. **Top 3 Termos:** Imprime os 3 termos com maiores diferenças para inspeção detalhada.

---

## 3. Como explicar a "Divergência" e por que ela varia entre execuções?

### *Pergunta que podem fazer na reunião:*
> *"Por que existe essa divergência de $10^{-14}$ a $10^{-16}$ e por que os últimos dígitos podem mudar ligeiramente de uma máquina para outra?"*

### *Sua Resposta Técnica:*
1. **A divergência é erro de máquina (ponto flutuante), não erro de código:**
   - Em computadores, números decimais são armazenados em precisão dupla (padrão **IEEE 754 / float64**), que possui 53 bits de precisão (~15 a 17 dígitos significativos). O limite de precisão do computador ($\epsilon_{\text{máquina}}$) é $\approx 2{,}22 \times 10^{-16}$.
   - Quando o Ket e o OpenFermion somam centenas de matrizes e produtos tensoriais para gerar o Hamiltoniano, os arredondamentos nos últimos bits se acumulam na ordem de $10^{-14}$ a $10^{-16}$.

2. **Por que pequenas variações no último dígito acontecem entre execuções/máquinas?**
   - **Ordem de soma em ponto flutuante:** Na matemática teórica, $(a + b) + c = a + (b + c)$. Em computadores, devido ao arredondamento binário, a ordem da soma altera os últimos bits.
   - **Bibliotecas de álgebra linear (BLAS/LAPACK):** O PySCF utiliza rotinas paralelizadas em C/Fortran (OpenBLAS/MKL). Se o escalonador de threads do processador distribuir os cálculos em ordens ligeiramente diferentes (ou entre o Windows/WSL e outro Linux), a 15ª casa decimal terá uma oscilação infinitesimal.
   - **Escala dos coeficientes:** Para a molécula de $\text{H}_2\text{O}$, o coeficiente do termo identidade é $\approx -46{,}42$. Uma diferença de $3{,}55 \times 10^{-14}$ em relação a $46{,}42$ representa um **erro relativo de $7{,}6 \times 10^{-16}$** (isto é, 15 casas decimais idênticas).

3. **Conclusão:**
   - Essas divergências comprovam que **a formulação algébrica do Ket é matematicamente exata** e que toda e qualquer discrepância observada é puramente ruído numérico de ponto flutuante da máquina.
