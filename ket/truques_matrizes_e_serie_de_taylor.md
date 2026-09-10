# Truques de Álgebra Linear & Dedução da Série de Taylor para Matrizes

> **Objetivo:** 
> 1. Aprender o **truque visual** para "bater o olho" em qualquer matriz e saber o que ela faz com as bases (sem fazer contas).
> 2. Entender como a **Série de Taylor** funciona para matrizes e deduzir passo a passo como $\exp(\theta G)$ vira a matriz de rotação $\begin{bmatrix} \cos\theta & -\sin\theta \\ \sin\theta & \cos\theta \end{bmatrix}$.

---

## 1. O Truque Visual: "Bater o Olho" em uma Matriz

Em Álgebra Linear e Computação Quântica, existe um segredo fundamental que quase nenhum professor ensina de forma direta:

> 💡 **Regra de Ouro:** **As colunas de uma matriz são EXATAMENTE para onde as bases vão!**

Uma matriz $2 \times 2$:
$$M = \begin{bmatrix} \color{blue}{a} & \color{red}{b} \\ \color{blue}{c} & \color{red}{d} \end{bmatrix}$$

* A **1ª Coluna** $\begin{bmatrix} \color{blue}{a} \\ \color{blue}{c} \end{bmatrix}$ diz: *"O que acontece quando a entrada é a primeira base $\begin{bmatrix} 1 \\ 0 \end{bmatrix}$ ($|1100\rangle$)"*.
* A **2ª Coluna** $\begin{bmatrix} \color{red}{b} \\ \color{red}{d} \end{bmatrix}$ diz: *"O que acontece quando a entrada é a segunda base $\begin{bmatrix} 0 \\ 1 \end{bmatrix}$ ($|0011\rangle$)"*.

---

### Vamos treinar o "bater o olho":

#### Exemplo 1: O Operador de Ida $T$
$$T = \begin{bmatrix} \color{blue}{0} & \color{red}{0} \\ \color{blue}{1} & \color{red}{0} \end{bmatrix}$$
* Olhe para a **1ª Coluna**: $\begin{bmatrix} \color{blue}{0} \\ \color{blue}{1} \end{bmatrix}$. Ela é o vetor da segunda base ($|0011\rangle$).  
  $\implies$ **Significado:** Ela pega a 1ª base e **joga na 2ª base** (o pulo de ida!).
* Olhe para a **2ª Coluna**: $\begin{bmatrix} \color{red}{0} \\ \color{red}{0} \end{bmatrix}$. É zero!  
  $\implies$ **Significado:** Se já estiver na 2ª base, ela **destrói** o estado (dá zero).

---

#### Exemplo 2: O Operador de Volta $T^\dagger$
$$T^\dagger = \begin{bmatrix} \color{blue}{0} & \color{red}{1} \\ \color{blue}{0} & \color{red}{0} \end{bmatrix}$$
* Olhe para a **1ª Coluna**: $\begin{bmatrix} \color{blue}{0} \\ \color{blue}{0} \end{bmatrix} \implies$ Dá zero na 1ª base.
* Olhe para a **2ª Coluna**: $\begin{bmatrix} \color{red}{1} \\ \color{red}{0} \end{bmatrix} \implies$ Pega a 2ª base e **joga de volta na 1ª base**!

---

#### Exemplo 3: A Porta Pauli X (Porta NOT)
$$X = \begin{bmatrix} \color{blue}{0} & \color{red}{1} \\ \color{blue}{1} & \color{red}{0} \end{bmatrix}$$
* 1ª Coluna: $\begin{bmatrix} \color{blue}{0} \\ \color{blue}{1} \end{bmatrix} \implies |0\rangle$ vira $|1\rangle$.
* 2ª Coluna: $\begin{bmatrix} \color{red}{1} \\ \color{red}{0} \end{bmatrix} \implies |1\rangle$ vira $|0\rangle$.
* Só de bater o olho, você vê que é uma inversão (NOT)!

---

## 2. Como Exponencial de Matriz Vira uma Matriz? (Série de Taylor)

No cálculo com números normais (escalares $x$), a **Série de Taylor** de $e^x$ é:
$$e^x = 1 + x + \frac{x^2}{2!} + \frac{x^3}{3!} + \frac{x^4}{4!} + \dots = \sum_{k=0}^{\infty} \frac{x^k}{k!}$$

### Como isso se aplica a Matrizes?
Para uma matriz quadrada $M$, a definição é **idêntica**, trocando o número $1$ pela **Matriz Identidade $I$**:
$$\exp(M) = I + M + \frac{M^2}{2!} + \frac{M^3}{3!} + \frac{M^4}{4!} + \dots$$

Como $M^2 = M \cdot M$ é só multiplicação de matrizes, e somar matrizes é só somar elemento por elemento, **a soma infinita de matrizes resulta em uma nova matriz!**

---

## 3. Dedução Passo a Passo: De $\exp(\theta G)$ até a Matriz de Seno e Cosseno

Nosso gerador do UCCSD é:
$$G = T - T^\dagger = \begin{bmatrix} 0 & 0 \\ 1 & 0 \end{bmatrix} - \begin{bmatrix} 0 & 1 \\ 0 & 0 \end{bmatrix} = \begin{bmatrix} 0 & -1 \\ 1 & 0 \end{bmatrix}$$

Queremos calcular $\exp(\theta G) = \exp\left(\begin{bmatrix} 0 & -\theta \\ \theta & 0 \end{bmatrix}\right)$.

### Passo 1: Calcular as potências de $G$ (Observe o padrão cíclico!)
* $G^0 = I = \begin{bmatrix} 1 & 0 \\ 0 & 1 \end{bmatrix}$
* $G^1 = G = \begin{bmatrix} 0 & -1 \\ 1 & 0 \end{bmatrix}$
* $G^2 = G \cdot G = \begin{bmatrix} 0 & -1 \\ 1 & 0 \end{bmatrix} \begin{bmatrix} 0 & -1 \\ 1 & 0 \end{bmatrix} = \begin{bmatrix} -1 & 0 \\ 0 & -1 \end{bmatrix} = \mathbf{-I}$
* $G^3 = G^2 \cdot G = (-I) \cdot G = \mathbf{-G}$
* $G^4 = G^2 \cdot G^2 = (-I) \cdot (-I) = \mathbf{I}$ (voltou ao início!)

> 🌟 **Padrão:**
> * As potências **pares** ($G^0, G^2, G^4, \dots$) são múltiplos de **$I$**: $+I, -I, +I, -I, \dots$
> * As potências **ímpares** ($G^1, G^3, G^5, \dots$) são múltiplos de **$G$**: $+G, -G, +G, -G, \dots$

---

### Passo 2: Substituir na Série de Taylor
$$\exp(\theta G) = I + (\theta G) + \frac{(\theta G)^2}{2!} + \frac{(\theta G)^3}{3!} + \frac{(\theta G)^4}{4!} + \frac{(\theta G)^5}{5!} + \dots$$

Separamos os termos pares (que têm $I$) dos termos ímpares (que têm $G$):

$$\exp(\theta G) = I \left( 1 - \frac{\theta^2}{2!} + \frac{\theta^4}{4!} - \dots \right) + G \left( \theta - \frac{\theta^3}{3!} + \frac{\theta^5}{5!} - \dots \right)$$

---

### Passo 3: Reconhecer as Séries de Taylor de Cosseno e Seno!
Do cálculo clássico:
* $\cos(\theta) = 1 - \frac{\theta^2}{2!} + \frac{\theta^4}{4!} - \dots$
* $\sin(\theta) = \theta - \frac{\theta^3}{3!} + \frac{\theta^5}{5!} - \dots$

Substituindo essas funções na nossa equação:
$$\exp(\theta G) = \cos(\theta) \cdot I + \sin(\theta) \cdot G$$

---

### Passo 4: Montar a Matriz Final
Agora substituímos as matrizes $I$ e $G$:

$$\exp(\theta G) = \cos(\theta) \begin{bmatrix} 1 & 0 \\ 0 & 1 \end{bmatrix} + \sin(\theta) \begin{bmatrix} 0 & -1 \\ 1 & 0 \end{bmatrix}$$

$$= \begin{bmatrix} \cos(\theta) & 0 \\ 0 & \cos(\theta) \end{bmatrix} + \begin{bmatrix} 0 & -\sin(\theta) \\ \sin(\theta) & 0 \end{bmatrix}$$

$$= \begin{bmatrix} \cos(\theta) & -\sin(\theta) \\ \sin(\theta) & \cos(\theta) \end{bmatrix}$$

---

## 4. O Que Essa Matriz Faz (Usando o Truque do "Bater o Olho")

Olhe para a matriz final que deduzimos:
$$U(\theta) = \begin{bmatrix} \color{blue}{\cos\theta} & \color{red}{-\sin\theta} \\ \color{blue}{\sin\theta} & \color{red}{\cos\theta} \end{bmatrix}$$

* **1ª Coluna** $\begin{bmatrix} \color{blue}{\cos\theta} \\ \color{blue}{\sin\theta} \end{bmatrix}$:
  Se você começar com o estado inicial $|1100\rangle$, ele vai virar:
  $$\cos(\theta)|1100\rangle + \sin(\theta)|0011\rangle$$
* **2ª Coluna** $\begin{bmatrix} \color{red}{-\sin\theta} \\ \color{red}{\cos\theta} \end{bmatrix}$:
  Se você começar com o estado excitado $|0011\rangle$, ele vai virar:
  $$-\sin(\theta)|1100\rangle + \cos(\theta)|0011\rangle$$

Viu como tudo se conecta? A série de Taylor é apenas a ferramenta matemática para transformar uma operação de troca ($G$) em uma rotação contínua suave ($U(\theta)$)!
