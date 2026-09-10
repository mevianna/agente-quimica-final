# Resultados e Discussão

O componente `ket.fermion` fornece a infraestrutura simbólica para representação e manipulação de operadores em segunda quantização. Entre as principais funcionalidades implementadas, destacam-se:

- **Composição de produtos e combinações lineares:** permite representar produtos de operadores de criação e aniquilação, como $a^\dagger_0 a_1$, e construir combinações lineares com coeficientes reais ou complexos, como $1{,}5 a^\dagger_0 a_0 + (0{,}2 + 0{,}5i) a^\dagger_0 a_1$.

- **Simplificação numérica:** remove termos cujos coeficientes apresentam magnitude inferior à tolerância definida. Para $\text{tol} = 10^{-8}$, por exemplo, $0{,}5 a^\dagger_0 a_1 + 10^{-10} a^\dagger_1 a_0$ é reduzido a $0{,}5 a^\dagger_0 a_1$.

- **Ordenação normal:** reorganiza os operadores de modo que os de criação precedam os de aniquilação, aplicando as relações de anticomutação fermiônicas necessárias. Por exemplo, $a_1 a^\dagger_1$ é transformado em $I - a^\dagger_1 a_1$. Em expressões complexas envolvendo múltiplos orbitais, os índices dos orbitais são ordenados de forma decrescente, do maior para o menor, enquanto termos semelhantes são agrupados e coeficientes inferiores à tolerância são automaticamente eliminados, garantindo uma representação canônica única.

- **Verificação da conservação do número de partículas:** verifica se cada termo possui quantidade igual de operadores de criação e aniquilação. Assim, $a^\dagger_0 a_1$ é classificado como conservador, enquanto $a^\dagger_0 a^\dagger_1$ não conserva o número total de partículas.

- **Verificação da conservação de $S_z$:** avalia separadamente os balanços de criação e aniquilação dos operadores associados aos spins $\alpha$ e $\beta$, permitindo verificar a conservação da componente $z$ do spin.

- **Validação de operadores de até dois corpos:** verifica se cada termo contém no máximo quatro operadores fermiônicos, correspondentes à identidade, a termos de um corpo (como $a^\dagger_0 a_1$) ou de dois corpos (como $a^\dagger_0 a^\dagger_1 a_3 a_2$), e se o operador conserva o número de partículas.

Para avaliar o comportamento prático dos mapeamentos implementados, analisou-se a transformação de um mesmo operador fermiônico, correspondente ao termo de acoplamento entre os spin-orbitais não vizinhos 3 e 7, $a^\dagger_3 a_7$, responsável por aniquilar um elétron no orbital 7 (inicialmente ocupado) e criá-lo no orbital 3 (inicialmente vazio), em um sistema com $N = 8$ spin-orbitais e 4 elétrons, com $n_\alpha = n_\beta = 2$. A aplicação dos quatro mapeamentos evidencia diferenças na estrutura das cadeias de operadores de Pauli e, no caso do SCBK, no número de qubits utilizado. Segue a descrição de cada um dos mapeamentos:

### Jordan-Wigner (JW)

**8 qubits necessários**

$$\text{JW}(a^\dagger_3 a_7) = -0{,}25j \cdot Y_3 Z_4 Z_5 Z_6 X_7 + (0{,}25 - 0j) \cdot Y_3 Z_4 Z_5 Z_6 Y_7 + (0{,}25 + 0j) \cdot X_3 Z_4 Z_5 Z_6 X_7 + 0{,}25j \cdot X_3 Z_4 Z_5 Z_6 Y_7$$

Neste mapeamento, cada qubit corresponde diretamente a um spin-orbital (exigindo os 8 qubits). Como os orbitais 3 e 7 não são adjacentes, a transformação introduz a cadeia de operadores de fase $Z_4 Z_5 Z_6$ nos qubits intermediários, fazendo com que cada termo resultante atue sobre 5 qubits simultaneamente.

### Paridade

**8 qubits necessários**

$$\text{Parity}(a^\dagger_3 a_7) = -0{,}25j \cdot Z_2 X_3 X_4 X_5 Y_6 + (-0{,}25 + 0j) \cdot Z_2 X_3 X_4 X_5 X_6 Z_7 + (-0{,}25 + 0j) \cdot Y_3 X_4 X_5 Y_6 + 0{,}25j \cdot Y_3 X_4 X_5 X_6 Z_7$$

A transformação armazena a paridade acumulada da ocupação dos orbitais anteriores. Como ainda representa a totalidade do espaço de estados sem redução de simetria, são necessários os mesmos 8 qubits, gerando operadores que atuam nos qubits de 2 a 7.

### Bravyi-Kitaev (BK)

**8 qubits necessários**

$$\text{BK}(a^\dagger_3 a_7) = -0{,}25j \cdot Z_1 Z_2 Y_3 Z_5 Z_6 + (-0{,}25 + 0j) \cdot Z_1 Z_2 X_3 Z_7 + (0{,}25 + 0j) \cdot X_3 Z_5 Z_6 + 0{,}25j \cdot Y_3 Z_7$$

O mapeamento BK também necessita de 8 qubits para representar a totalidade dos spin-orbitais. No entanto, ao distribuir a informação por meio de uma árvore de Fenwick, em vez de uma cadeia linear, reduz-se a necessidade de sequências contínuas de operadores $Z$ nos qubits intermediários, resultando, em geral, em termos que atuam simultaneamente sobre um número menor de qubits.

### Bravyi-Kitaev com Simetria (SCBK)

**6 qubits necessários**

$$\text{SCBK}(a^\dagger_3 a_7) = -0{,}25j \cdot Z_3 Y_4 Z_5 + (-0{,}25 + 0j) \cdot Z_3 X_4 + (0{,}25 + 0j) \cdot X_4 Z_5 + 0{,}25j \cdot Y_4$$

O método SCBK explora a conservação do número de partículas em cada setor de spin ($n_\alpha = 2$ e $n_\beta = 2$). Como as paridades totais de cada setor de spin são constantes e conhecidas a priori, os 2 qubits associados a essas simetrias podem ser eliminados matematicamente (*tapering off*). Isso reduz o registrador de 8 para 6 qubits e simplifica os operadores resultantes.

Tais mapeamentos foram confrontados com implementações de referência. Para os mapeamentos Jordan-Wigner, Bravyi-Kitaev e SCBK, os resultados foram comparados com as implementações correspondentes da biblioteca OpenFermion, enquanto o mapeamento por Paridade foi validado em comparação com a biblioteca PennyLane. Para o operador $a^\dagger_3 a_7$, as representações obtidas apresentaram concordância nos coeficientes e na estrutura algébrica, considerando as respectivas convenções de ordenação dos termos. No caso do SCBK, ambas as implementações resultaram na redução do registrador de oito para seis qubits.

A validação dos coeficientes do Hamiltoniano molecular gerados pelo Ket foi realizada por meio de comparação direta com os resultados da biblioteca OpenFermion para as moléculas de $\text{H}_2$, $\text{LiH}$, $\text{BeH}_2$ e $\text{H}_2\text{O}$ na base STO-3G após o mapeamento Jordan-Wigner. 

Após a transformação fermiônica, cada Hamiltoniano é representado no espaço de qubits como uma combinação linear de cadeias de operadores de Pauli:
$$H = \sum_k c_k P_k$$
onde $P_k$ denota uma cadeia de operadores de Pauli ($I, X, Y, Z$) e $c_k$ seu respectivo coeficiente real. A **divergência** termo a termo avalia a diferença absoluta entre os coeficientes calculados por ambas as bibliotecas ($\Delta_k = |c_k^{(\text{Ket})} - c_k^{(\text{OpenFermion})}|$), enquanto a **divergência máxima** ($\Delta_{\max}$) expressa o maior desvio absoluto observado em todo o espectro de termos do Hamiltoniano:
$$\Delta_{\max} = \max_k \left| c_k^{(\text{Ket})} - c_k^{(\text{OpenFermion})} \right|$$

A Tabela 1 apresenta o número de qubits, o número de termos de Pauli gerados e a divergência máxima entre os coeficientes calculados pelo Ket e pelo OpenFermion. Em todos os casos, a divergência máxima manteve-se estritamente na ordem de $10^{-16}$ a $10^{-14}$, magnitude compatível com os limites de precisão de máquina em aritmética de ponto flutuante de dupla precisão (padrão IEEE 754), comprovando a exatidão numérica e a equivalência algébrica da implementação.

| Molécula | Número de qubits | Número de termos | Divergência Máxima ($\Delta_{\max}$) |
| :---: | :---: | :---: | :---: |
| $\text{H}_2$ | 4 | 15 | $1{,}80 \times 10^{-16}$ |
| $\text{LiH}$ | 12 | 631 | $1{,}17 \times 10^{-14}$ |
| $\text{BeH}_2$ | 14 | 666 | $2{,}55 \times 10^{-15}$ |
| $\text{H}_2\text{O}$ | 14 | 1086 | $7{,}11 \times 10^{-15}$ |

*Tabela 1: Comparação dos coeficientes dos Hamiltonianos obtidos pelo Ket e pelo OpenFermion na base STO-3G com mapeamento Jordan-Wigner.*
