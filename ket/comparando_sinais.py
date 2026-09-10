import pennylane as qml
from pennylane import numpy as np
from openfermion.chem import MolecularData
from openfermionpyscf import run_pyscf
from openfermion.transforms import get_fermion_operator, normal_ordered
from openfermion import FermionOperator

def convert_pl_to_openfermion(H_pl):
    """Converte o dicionário de FermionSentence do PennyLane para FermionOperator do OpenFermion."""
    of_op = FermionOperator.zero()
    for pl_word, coef in H_pl.items():
        term_tuples = []
        for k, op in pl_word.items():
            wire = k[1] if isinstance(k, tuple) else int(k)
            action = 1 if op == '+' else 0
            term_tuples.append((wire, action))
        
        term_str = " ".join([f"{wire}^" if act == 1 else f"{wire}" for wire, act in term_tuples])
        of_op += FermionOperator(term_str, float(coef))
    return of_op

# ==========================================
# 1. PARAMETRIZAÇÃO UNIFICADA
# ==========================================
dist_angstrom = 1.595  # Distância interpolação em Angstrom
symbols = ["Li", "H"]
geometry_ang = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, dist_angstrom]])

# ==========================================
# 2. GERAR HAMILTONIANOS
# ==========================================
# Usamos method="pyscf" no PennyLane para evitar o solver experimental/diferenciável (dhf)
mol_pl = qml.qchem.Molecule(symbols, geometry_ang, unit="angstrom")
H_pl = qml.qchem.fermionic_hamiltonian(mol_pl, method="pyscf")()
H_pl_of = convert_pl_to_openfermion(H_pl)

# OpenFermion
geometry_of = [('Li', (0.0, 0.0, 0.0)), ('H', (0.0, 0.0, dist_angstrom))]
molecule_of = MolecularData(geometry_of, 'sto-3g', 1, 0)
molecule_of = run_pyscf(molecule_of, run_scf=True)
H_of = get_fermion_operator(molecule_of.get_molecular_hamiltonian())

# ==========================================
# 3. NORMAL ORDERING (ORDENAÇÃO CANÔNICA)
# ==========================================
H_pl_norm = normal_ordered(H_pl_of)
H_of_norm = normal_ordered(H_of)

terms_pl = H_pl_norm.terms
terms_of = H_of_norm.terms

all_keys = set(terms_pl.keys()).union(set(terms_of.keys()))

# ==========================================
# 4. CLASSIFICAÇÃO AUTOMÁTICA DE DIVERGÊNCIAS
# ==========================================
exact_matches = []
pure_sign_flips = []
magnitude_diffs = []
missing_in_pl = []
missing_in_of = []

tol = 1e-5

for key in all_keys:
    in_pl = key in terms_pl
    in_of = key in terms_of
    
    c_pl = terms_pl.get(key, 0.0)
    c_of = terms_of.get(key, 0.0)
    
    if abs(c_pl) < tol and abs(c_of) < tol:
        continue
        
    if not in_pl:
        missing_in_pl.append((key, c_of))
        continue
    if not in_of:
        missing_in_of.append((key, c_pl))
        continue
        
    diff = c_pl - c_of
    sum_val = c_pl + c_of
    
    if abs(diff) < tol:
        exact_matches.append((key, c_pl))
    elif abs(sum_val) < tol:
        # Mesma magnitude, mas sinal oposto (+X vs -X) mesmo após ordenação normal
        pure_sign_flips.append((key, c_pl, c_of))
    else:
        magnitude_diffs.append((key, c_pl, c_of, diff))

# ==========================================
# 5. RELATÓRIO PARA O ORIENTADOR
# ==========================================
print("=========================================================================")
print("          RELATÓRIO DIAGNÓSTICO: PENNYLANE VS OPENFERMION                ")
print("=========================================================================")
print(f"Total de termos fermiônicos analisados: {len(all_keys)}")
print(f"1. Coincidências Exatas (Sinal E Magnitude):    {len(exact_matches)}")
print(f"2. Inversão Pura de Sinal (Fase MO do SCF):     {len(pure_sign_flips)}")
print(f"3. Divergência de Magnitude Real:               {len(magnitude_diffs)}")
print(f"4. Termos ausentes no PL / OF:                  {len(missing_in_pl) + len(missing_in_of)}")
print("-------------------------------------------------------------------------\n")

print("--- EXEMPLOS DE COINCIDÊNCIAS EXATAS (Sinal e Magnitude iguais) ---")
for key, coef in exact_matches[:5]:
    print(f"  Termo {key}: Coef = {coef:+.6f}")

if pure_sign_flips:
    print("\n--- EXEMPLOS DE INVERSÃO PURA DE SINAL (Fase Orbital do Hartree-Fock) ---")
    print("Nota: Estes termos têm magnitude idêntica, mas sinais opostos mesmo após Ordenação Normal.")
    for key, c_pl, c_of in pure_sign_flips[:8]:
        print(f"  Termo {key}: PL = {c_pl:+.6f} | OF = {c_of:+.6f}")

if magnitude_diffs:
    print("\n--- EXEMPLOS DE DIVERGÊNCIA REAL DE MAGNITUDE ---")
    for key, c_pl, c_of, diff in magnitude_diffs[:8]:
        print(f"  Termo {key}: PL = {c_pl:+.6f} | OF = {c_of:+.6f} | Diff = {diff:+.6f}")