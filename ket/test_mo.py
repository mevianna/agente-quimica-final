import pyscf

print("====================================================")
print("DEMONSTRAÇÃO DE GERAÇÃO DO ATRIBUTO 'mo_coeff' NO PySCF")
print("====================================================\n")

# 1. Definimos a molécula clássica (H2 a 0.74 Angstrom)
mol = pyscf.gto.M(atom='H 0 0 0; H 0 0 0.74', basis='sto-3g')

# 2. Instanciamos o solver clássico RHF
mf = pyscf.scf.RHF(mol)

print("--- ANTES DE EXECUTAR O CÁLCULO SCF ---")
print(f"O atributo 'mo_coeff' existe? {hasattr(mf, 'mo_coeff')}")
print(f"Qual o valor atual dele? {getattr(mf, 'mo_coeff', None)}")
print("-" * 40)

# 3. Executamos o cálculo clássico
print("\n[Executando o cálculo de Hartree-Fock clássico com mf.kernel() ...]")
energia_scf = mf.kernel()

print("\n--- DEPOIS DE EXECUTAR O CÁLCULO SCF ---")
print(f"O atributo 'mo_coeff' existe? {hasattr(mf, 'mo_coeff')}")
print(f"Tipo da variável 'mo_coeff': {type(mf.mo_coeff)}")
print(f"Dimensões da matriz: {mf.mo_coeff.shape} (2 orbitais atômicos x 2 orbitais moleculares)")
print("\nConteúdo da matriz 'mo_coeff' (Coeficientes):")
print(mf.mo_coeff)
print("====================================================")
