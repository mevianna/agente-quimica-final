#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validação e Comparação dos Coeficientes dos Hamiltonianos Mapeados (Jordan-Wigner)
entre as plataformas Ket e OpenFermion para as moléculas: H2, LiH, BeH2 e H2O.

Este script executa:
1. Cálculo Hartree-Fock Restrito (RHF) com base STO-3G via PySCF integrado no Ket.
2. Cálculo de referência via OpenFermion + OpenFermion-PySCF.
3. Transformação Jordan-Wigner para representação em qubits (operadores de Pauli).
4. Análise estatística termo a termo (Divergência Máxima, Média, Contagem de Termos e Qubits).
5. Geração automática da Tabela formatada para o artigo (Markdown e LaTeX).
"""

import os
import sys
import numpy as np

# Adiciona o caminho do código-fonte do Ket local caso não esteja instalado como pacote global
current_dir = os.path.dirname(os.path.abspath(__file__))
ket_src_path = os.path.join(current_dir, "ket", "src")
if os.path.exists(ket_src_path) and ket_src_path not in sys.path:
    sys.path.insert(0, ket_src_path)

try:
    import ket
    from ket.chem import fermionic_hamiltonian, jordan_wigner as ket_jw
    from ket.base import Process
except ImportError as e:
    print(f"[ERRO] Não foi possível importar o Ket: {e}")
    print("Certifique-se de estar com o ambiente virtual ativado no WSL.")
    sys.exit(1)

try:
    import pyscf
    from openfermion.chem import MolecularData
    from openfermionpyscf import run_pyscf
    from openfermion import get_fermion_operator, jordan_wigner as of_jw
except ImportError as e:
    print(f"[ERRO] Dependência ausente (PySCF ou OpenFermion): {e}")
    print("Instale no WSL: pip install pyscf openfermion openfermion-pyscf")
    sys.exit(1)


def ket_hamiltonian_to_dict(h_ket):
    """Converte o Hamiltoniano de qubits do Ket para dicionário canônico {pauli_string: coef_complex}.
    
    Verifica rigorosamente que a parte imaginária de todos os coeficientes seja nula (dentro da precisão numérica).
    """
    d = {}
    for term in h_ket.terms:
        c_complex = complex(term.coef)
        assert abs(c_complex.imag) < 1e-12, f"[ERRO FÍSICO] Coeficiente com parte imaginária no Ket: {term.coef}"
        clean_map = {q: p for q, p in term.map.items() if p != "I"}
        key = "I" if not clean_map else " ".join(f"{p}{q}" for q, p in sorted(clean_map.items()))
        d[key] = d.get(key, 0j) + c_complex
    return d


def openfermion_hamiltonian_to_dict(h_of_qubit):
    """Converte o QubitOperator do OpenFermion para dicionário canônico {pauli_string: coef_complex}.
    
    Verifica rigorosamente que a parte imaginária de todos os coeficientes seja nula (dentro da precisão numérica).
    """
    of_dict = {}
    for term, coef in h_of_qubit.terms.items():
        c_complex = complex(coef)
        assert abs(c_complex.imag) < 1e-12, f"[ERRO FÍSICO] Coeficiente com parte imaginária no OpenFermion: {coef}"
        if not term:
            key = "I"
        else:
            paulis = [f"{op}{q_idx}" for q_idx, op in term]
            paulis.sort(key=lambda x: int(x[1:]))
            key = " ".join(paulis)
        of_dict[key] = of_dict.get(key, 0j) + c_complex
    return of_dict


def analisar_molecula(nome_molecula, symbols, coordinates, basis="sto-3g"):
    """Compara o Hamiltoniano mapeado via Jordan-Wigner do Ket com o OpenFermion."""
    print(f"\n{'='*75}")
    print(f" Molécula: {nome_molecula} | Base: {basis} | Geometria: {symbols}")
    print(f"{'='*75}")

    # =========================================================================
    # 1. Pipeline do KET:
    # =========================================================================
    # 1.1 Calcula as integrais moleculares via Hartree-Fock Restrito (RHF com PySCF)
    #     e constrói o operador fermiônico em segunda quantização.
    h_fermion_ket = fermionic_hamiltonian(symbols, coordinates, basis=basis)
    
    # 1.2 Determina o número total de spin-orbitais (qubits necessários).
    n_qubits = max(op.orbital for term in h_fermion_ket for op in term.operators if term.operators) + 1
    
    # 1.3 Aloca os qubits no processo do Ket e aplica a transformação Jordan-Wigner nativa.
    p = Process()
    q = p.alloc(n_qubits)
    h_qubit_ket = ket_jw(h_fermion_ket, q)
    
    # 1.4 Converte a estrutura de dados do Ket para um dicionário canônico {pauli_string: coef}.
    ket_dict = ket_hamiltonian_to_dict(h_qubit_ket)

    # =========================================================================
    # 2. Pipeline do OPENFERMION (Referência):
    # =========================================================================
    # 2.1 Constrói o objeto molecular e executa o cálculo SCF via PySCF integrado ao OpenFermion.
    geometry_of = [(sym, tuple(coords)) for sym, coords in zip(symbols, coordinates)]
    mol_of = MolecularData(geometry_of, basis=basis, multiplicity=1, charge=0)
    mol_of = run_pyscf(mol_of, run_scf=True)
    
    # 2.2 Extrai o operador fermiônico de interação e aplica a transformação Jordan-Wigner do OpenFermion.
    interaction_op = mol_of.get_molecular_hamiltonian()
    of_fermion = get_fermion_operator(interaction_op)
    of_qubit = of_jw(of_fermion)
    
    # 2.3 Converte o QubitOperator do OpenFermion para o mesmo formato canônico {pauli_string: coef}.
    of_dict = openfermion_hamiltonian_to_dict(of_qubit)

    # =========================================================================
    # 3. Verificação de Hermiticidade (Consistência Física):
    # =========================================================================
    # Garante que as partes imaginárias de todos os coeficientes sejam nulas (ruído numérico < 1e-12),
    # validando que os operadores gerados representam observáveis físicos reais (H = H†).
    max_imag_ket = max([abs(c.imag) for c in ket_dict.values()]) if ket_dict else 0.0
    max_imag_of = max([abs(c.imag) for c in of_dict.values()]) if of_dict else 0.0

    # =========================================================================
    # 4. Comparação Termo a Termo e Métricas Estatísticas:
    # =========================================================================
    # 4.1 Cria a UNIÃO de todas as chaves (strings de Pauli) encontradas em ambas as bibliotecas.
    #     Isso garante que se qualquer uma das bibliotecas gerar um termo a mais ou a menos,
    #     esse termo será detectado e comparado contra zero, evidenciando qualquer discrepância.
    #     O 'sorted' garante uma ordenação alfabética determinística dos termos.
    all_pauli_keys = sorted(list(set(ket_dict.keys()).union(set(of_dict.keys()))))
    
    divergencias = []
    detalhes_termos = []
    
    for key in all_pauli_keys:
        # Recupera o coeficiente do termo em cada biblioteca (retorna 0j se o termo não existir)
        c_ket = ket_dict.get(key, 0j)
        c_of = of_dict.get(key, 0j)
        
        # Calcula a diferença como a norma complexa |c_ket - c_of| (distância no plano complexo).
        # Isso testa simultaneamente a concordância da parte real e a ausência de parte imaginária espúria.
        diff = abs(c_ket - c_of)  # Módulo do número complexo |Δ|
        divergencias.append(diff)
        detalhes_termos.append((key, c_ket.real, c_of.real, diff))

    # 4.2 Divergência Máxima (norma do infinito ||Δ||_∞) e Divergência Média
    max_diff = max(divergencias) if divergencias else 0.0
    mean_diff = np.mean(divergencias) if divergencias else 0.0
    termos_ket = len(ket_dict)
    termos_of = len(of_dict)

    # 4.3 Ordena os termos em ordem decrescente de divergência para auditoria dos piores casos
    detalhes_termos.sort(key=lambda x: x[3], reverse=True)

    # Exibição dos resultados e estatísticas no terminal
    print(f"  • Qubits:                      {n_qubits}")
    print(f"  • Termos de Pauli (Ket):       {termos_ket}")
    print(f"  • Termos de Pauli (OF):        {termos_of}")
    print(f"  • Total de Termos Únicos:      {len(all_pauli_keys)}")
    print(f"  • Max |Imag| (Ket):            {max_imag_ket:.3e}")
    print(f"  • Max |Imag| (OF):             {max_imag_of:.3e}")
    print(f"  • Divergência Máxima (|Δ|):    {max_diff:.3e}")
    print(f"  • Divergência Média (|Δ|):     {mean_diff:.3e}")
    
    print("\n  Top 3 termos com maiores divergências:")
    for key, c_ket, c_of, diff in detalhes_termos[:3]:
        print(f"    - Termo '{key:15s}': Ket = {c_ket:+.8f} | OF = {c_of:+.8f} | |Δ| = {diff:.3e}")

    return {
        "molecula": nome_molecula,
        "n_qubits": n_qubits,
        "termos": len(all_pauli_keys),
        "max_imag_ket": max_imag_ket,
        "max_imag_of": max_imag_of,
        "max_diff": max_diff,
        "mean_diff": mean_diff,
    }


def main():
    print("#########################################################################")
    print("#  VALIDAÇÃO CRUZADA: HAMILTONIANOS MOLECULARES (KET vs OPENFERMION)    #")
    print("#########################################################################")

    # Geometrias padrão de teste
    moleculas = [
        {
            "nome": "H₂",
            "nome_latex": "$\\text{H}_2$",
            "symbols": ["H", "H"],
            "coords": [(0.0, 0.0, 0.0), (0.0, 0.0, 0.74)],
        },
        {
            "nome": "LiH",
            "nome_latex": "\\text{LiH}",
            "symbols": ["Li", "H"],
            "coords": [(0.0, 0.0, 0.0), (0.0, 0.0, 1.595)],
        },
        {
            "nome": "BeH₂",
            "nome_latex": "\\text{BeH}_2",
            "symbols": ["H", "Be", "H"],
            "coords": [(0.0, 0.0, -1.326), (0.0, 0.0, 0.0), (0.0, 0.0, 1.326)],
        },
        {
            "nome": "H₂O",
            "nome_latex": "\\text{H}_2\\text{O}",
            "symbols": ["O", "H", "H"],
            "coords": [
                (0.0, 0.0, 0.11779),
                (0.0, 0.755453, -0.471161),
                (0.0, -0.755453, -0.471161),
            ],
        },
    ]

    resultados = []
    for mol in moleculas:
        res = analisar_molecula(mol["nome"], mol["symbols"], mol["coords"])
        res["nome_latex"] = mol["nome_latex"]
        resultados.append(res)

    # -------------------------------------------------------------------------
    # TABELA FORMATADA (MARKDOWN / TEXTO)
    # -------------------------------------------------------------------------
    print("\n\n" + "#"*75)
    print("#               TABELA 1: RESULTADOS COMPARATIVOS PARA O ARTIGO          #")
    print("#"*75 + "\n")

    header_md = "| Molécula | Número de Qubits | Número de Termos | Divergência Máxima | Divergência Média |"
    sep_md    = "|:--------:|:----------------:|:----------------:|:------------------:|:-----------------:|"
    print(header_md)
    print(sep_md)
    for r in resultados:
        print(f"| {r['molecula']:<8} | {r['n_qubits']:^16} | {r['termos']:^16} | {r['max_diff']:^18.2e} | {r['mean_diff']:^17.2e} |")

    # -------------------------------------------------------------------------
    # TABELA FORMATADA (LATEX)
    # -------------------------------------------------------------------------
    print("\n--- Código LaTeX da Tabela para o Artigo ---")
    print(r"""\begin{table}[htbp]
\centering
\caption{Comparação dos Hamiltonianos obtidos via Ket e OpenFermion na base STO-3G com mapeamento Jordan-Wigner.}
\label{tab:validacao_hamiltonianos}
\begin{tabular}{lccc}
\hline
\textbf{Molécula} & \textbf{Número de qubits} & \textbf{Número de termos} & \textbf{Divergência Máxima} \\
\hline""")
    for r in resultados:
        if r['max_diff'] == 0:
            diff_str = "$0$"
        else:
            base, exp = f"{r['max_diff']:.2e}".split('e')
            exp_int = int(exp)
            diff_str = f"${base} \\times 10^{{{exp_int}}}$"
        print(f"{r['nome_latex']} & {r['n_qubits']} & {r['termos']} & {diff_str} \\\\")
    print(r"""\hline
\end{tabular}
\end{table}""")
    print("\n=========================================================================\n")


if __name__ == "__main__":
    main()
