# Relatório de Análise Técnica: Implementação do BKS-UCCSD

Este documento apresenta a análise técnica detalhada do código [`uccsd_professor.txt`](file:///D:/inct/ket/uccsd_professor.txt), avaliando suas especificidades, as diferenças em relação às bibliotecas padrão da literatura (PennyLane e OpenFermion), e o plano de adaptação para integração nativa no **Ket**.

---

## 1. O que este UCCSD tem de diferente? Foi feito algo especial?

**Sim, foi implementada uma versão customizada do BKS-UCCSD (*Bravyi-Kitaev Superfast / Symmetry-Conserving UCCSD*).**

### O problema nas bibliotecas padrão:
- **PennyLane (`qml.UCCSD`):** O ansatz UCCSD nativo do PennyLane opera prioritariamente sob a transformação de **Jordan-Wigner** (usando portas `SingleExcitation` e `DoubleExcitation`). Ele **não** possui suporte nativo direto para gerar os circuitos variacionais parametrizados com redução de simetria SCBK.
- **OpenFermion:** Possui a função matemática de redução de simetria (`symmetry_conserving_bravyi_kitaev`), mas não é um framework de circuitos quânticos variacionais (não constrói portas nem otimiza parâmetros).

### A solução implementada no script:
1. **Geração dos Operadores Anti-Hermitianos em 2ª Quantização:**  
   Constrói os operadores de excitação simples ($G_1$) e duplas ($G_2$) garantindo a forma anti-hermitiana ($G = A - A^\dagger$, tal que $G^\dagger = -G$):
   $$G_1 = a_q^\dagger a_p - a_p^\dagger a_q$$
   $$G_2 = a_s^\dagger a_r^\dagger a_q a_p - a_p^\dagger a_q^\dagger a_r a_s$$

2. **Redução de 2 Qubits via SCBK (*Tapering-off*):**  
   Converte a representação fermiônica para o formato do OpenFermion e aplica o mapeamento **Symmetry-Conserving Bravyi-Kitaev (SCBK)**. O SCBK explora a conservação do número total de partículas ($N = N_\alpha + N_\beta$) e da projeção de spin ($S_z$), eliminando **2 qubits** do registrador quântico.

3. **Filtragem de Operadores Nulos no Espaço Reduzido:**  
   Ao fixar os valores das simetrias, alguns operadores de excitação tornam-se constantes ou nulos. O script filtra esses termos com `if len(scbk_gen.terms) > 0:`, economizando parâmetros no ansatz.

4. **Conversão para Geradores Hermitianos:**  
   Multiplica os operadores por $i$ ($1j \cdot G$) para torná-los hermitianos ($A_{\text{herm}} = i G$), permitindo que o PennyLane os utilize em evoluções unitárias parametrizadas da forma:
   $$U(\theta) = \exp(-i \theta A_{\text{herm}})$$

---

## 2. O que precisamos adaptar para integrar nativamente ao Ket?

No **Ket**, já temos toda a infraestrutura matemática implementada no módulo `ket.chem` (classes [`Fermion`](file:///D:/inct/ket/src/ket/chem/fermion.py), [`FermionSentence`](file:///D:/inct/ket/src/ket/chem/fermion.py) e a transformação [`symmetry_conserving_bravyi_kitaev`](file:///D:/inct/ket/src/ket/chem/mapping.py)). Isso nos permite **eliminar 100% as dependências externas do PennyLane e do OpenFermion**.

### Passos de Implementação no Ket:

1. **Gerador Nativo de Índices de Excitação:**
   Criar uma função utilitária para gerar as tuplas de excitação ocupados $\to$ virtuais com conservação de spin ($S_z$):
   - **Singles:** pares $(p, q)$ com $p < n_e$, $q \ge n_e$, e $p \equiv q \pmod 2$.
   - **Doubles:** quartetos $(p, q, r, s)$ preservando o spin total.

2. **Montagem Direta dos Operadores Fermiônicos no Ket:**
   Utilizar a classe `FermionSentence` do Ket para representar $a_q^\dagger a_p - a_p^\dagger a_q$ diretamente em Python.

3. **Mapeamento Direto com o SCBK do Ket:**
   Passar a sentença fermiônica diretamente para a função `ket.chem.symmetry_conserving_bravyi_kitaev(G, qubits, n_so, n_alpha, n_beta)`.

4. **Evolução Variacional no Simulador KBW:**
   Os operadores de Pauli gerados são encapsulados em instâncias de `Hamiltonian` do Ket, prontas para aplicação em circuitos VQE ou simulações via `expv`.

### Exemplo de Implementação Nativa no Ket:
```python
from itertools import combinations
from ket.chem import Fermion, FermionSentence, symmetry_conserving_bravyi_kitaev

def ket_bks_uccsd(n_electrons: int, n_spin_orbitals: int, qubits):
    """Gera os geradores UCCSD com redução de 2 qubits (SCBK) nativamente no Ket."""
    n_alpha = n_electrons // 2
    n_beta = n_electrons - n_alpha
    
    occupied = list(range(n_electrons))
    virtual = list(range(n_electrons, n_spin_orbitals))
    
    generators = []
    
    # 1. Single Excitations
    for p in occupied:
        for q in virtual:
            if p % 2 == q % 2:  # Conservação de spin
                G = FermionSentence([
                    Fermion([(q, "+"), (p, "-")], coef=1.0),
                    Fermion([(p, "+"), (q, "-")], coef=-1.0),
                ])
                H_scbk = symmetry_conserving_bravyi_kitaev(
                    G, qubits, n_spin_orbitals, n_alpha, n_beta
                )
                if len(H_scbk.terms) > 0:
                    generators.append(1j * H_scbk)

    # 2. Double Excitations (análogo para quartetos)
    for p, q in combinations(occupied, 2):
        for r, s in combinations(virtual, 2):
            if (p % 2 + q % 2) == (r % 2 + s % 2):
                G = FermionSentence([
                    Fermion([(s, "+"), (r, "+"), (q, "-"), (p, "-")], coef=1.0),
                    Fermion([(p, "+"), (q, "+"), (r, "-"), (s, "-")], coef=-1.0),
                ])
                H_scbk = symmetry_conserving_bravyi_kitaev(
                    G, qubits, n_spin_orbitals, n_alpha, n_beta
                )
                if len(H_scbk.terms) > 0:
                    generators.append(1j * H_scbk)

    return generators
```

---

## 3. Principais Pontos para Destacar na Reunião

1. **Vantagem Computacional (Menor Profundidade de Circuito):**
   * A redução de 2 qubits via SCBK (ex: de 14 para 12 na água $\text{H}_2\text{O}$, ou de 4 para 2 no $\text{H}_2$) diminui exponencialmente a quantidade de portas CNOT necessárias para sintetizar $\exp(-i \theta P)$, acelerando as iterações do VQE.
2. **Independência Total de Pacotes Externos:**
   * O código original precisava converter dados entre PennyLane e OpenFermion. Com o módulo `ket.chem`, todo o fluxo roda 100% nativo no Ket, com alto desempenho integrado ao simulador KBW (Rust/C++).
3. **Otimização de Parâmetros Variacionais:**
   * O descarte de geradores que se anulam após o SCBK (`len(terms) > 0`) previne o gasto de parâmetros livres redundantes no otimizador clássico.
