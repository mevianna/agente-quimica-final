"""Fermionic operators and utilities.

This module provides fermionic creation and annihilation operators,
fermionic operator sentences, and utilities for particle number
and spin conservation checks.
"""

# SPDX-FileCopyrightText: 2026 Maria Eduarda W. M. Vianna <maria.vianna@grad.ufsc.br>
# SPDX-FileCopyrightText: 2026 Erico Souza Teixeira <erico.teixeira@venturus.org.br>
#
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=invalid-name, protected-access
# pylint: disable=cell-var-from-loop, disable=too-many-locals

from copy import copy
from dataclasses import dataclass

__all__ = [
    "Fermion",
    "FermionOperator",
    "FermionSentence",
    "CreateFermion",
    "AnnihilateFermion",
    "number_operator",
]


# ======================================================
# SPIN RULE
# ======================================================

def _resolve_spin(orbital: int, spin: str | None):
    if spin is not None:
        if spin not in ("a", "b"):
            raise ValueError("spin must be 'a' or 'b'")
        return spin

    return "a" if orbital % 2 == 0 else "b"


# ======================================================
# WORD (PRODUCT)
# ======================================================

def _parse_dict_operators(operators: dict) -> list['FermionOperator']:
    parsed_ops = []
    # Sort keys by position (first element of key) to guarantee sequence order
    sorted_items = sorted(operators.items(), key=lambda x: x[0][0])
    for key, op in sorted_items:
        if len(key) == 2:
            _pos, orb = key
            spin = None
        elif len(key) == 3:
            _pos, orb, spin = key
        else:
            raise ValueError("key must be (pos, orb) or (pos, orb, spin)")

        if not isinstance(orb, int):
            raise TypeError("Orbital must be int")

        if orb < 0:
            raise ValueError("Orbital must be non-negative")

        if spin is None:
            spin = _resolve_spin(orb, None)

        if spin not in ("a", "b"):
            raise ValueError("Invalid spin")

        if op not in ("+", "-"):
            raise ValueError("Operator must be '+' or '-'")

        parsed_ops.append(FermionOperator(orb, spin, op))
    return parsed_ops


@dataclass(frozen=True)
class FermionOperator:
    """Fermionic operator representation (orbital, spin, action)."""
    orbital: int
    spin: str
    action: str  # '+' or '-'

@dataclass(frozen=True)
class Fermion:
    """Fermionic operator product.

    Represents an ordered product of fermionic creation and
    annihilation operators.
    """
    operators: tuple[FermionOperator, ...] = ()

    def __post_init__(self):
        if isinstance(self.operators, dict):
            parsed_ops = _parse_dict_operators(self.operators)
            object.__setattr__(self, 'operators', tuple(parsed_ops))

        elif isinstance(self.operators, (list, tuple)):
            for op in self.operators:
                if not isinstance(op, FermionOperator):
                    raise TypeError("All elements must be FermionOperator")
            object.__setattr__(self, 'operators', tuple(self.operators))
        else:
            raise TypeError("operators must be dict or tuple/list of FermionOperator")

    def __len__(self) -> int:
        return len(self.operators)

    def __getitem__(self, index: int) -> FermionOperator:
        return self.operators[index]

    def __str__(self):
        if not self.operators:
            return "I"

        out = []
        for op in self.operators:
            out.append(f"a⁺({op.orbital})" if op.action == "+" else f"a({op.orbital})")

        return " ".join(out)

    def _repr_latex_(self) -> str:
        """Default Jupyter LaTeX representation (no spin)."""
        return f"${self._latex_core(spin=False)}$"

    def _latex_core(self, spin=False) -> str:
        """Internal LaTeX builder (no math delimiters)."""
        if not self.operators:
            return "I"

        out = []
        for op in self.operators:
            idx = f"{op.orbital},{op.spin}" if spin else f"{op.orbital}"
            if op.action == "+":
                out.append(rf"a^{{\dagger}}_{{{idx}}}")
            else:
                out.append(rf"a_{{{idx}}}")

        return " ".join(out)

    def show(self, spin=False):
        """Return a string representation of the operator.

        Args:
            spin: Whether to include spin labels.

        Returns:
            Human-readable fermionic operator string.
        """
        if not self.operators:
            return "I"

        out = []
        for op in self.operators:
            if spin:
                if op.action == "+":
                    out.append(f"a⁺({op.orbital},{op.spin})")
                else:
                    out.append(f"a({op.orbital},{op.spin})")
            else:
                if op.action == "+":
                    out.append(f"a⁺({op.orbital})")
                else:
                    out.append(f"a({op.orbital})")

        return " ".join(out)

    def get_spin(self):
        """Return the spin associated with each operator."""
        return {(pos, op.orbital): op.spin for pos, op in enumerate(self.operators)}

    def adjoint(self):
        """Return the Hermitian adjoint of the fermionic operator."""
        reversed_ops = []
        for op in reversed(self.operators):
            new_op = "-" if op.action == "+" else "+"
            reversed_ops.append(FermionOperator(op.orbital, op.spin, new_op))
        return Fermion(tuple(reversed_ops))

    def normal_ordered(self, tol=1e-8):
        """Return the normal ordered form of the operator.

        Promotes the Fermion to a FermionSentence and applies normal ordering.
        """
        return FermionSentence({self: 1}).normal_ordered(tol)

    def __mul__(self, other):
        if isinstance(other, Fermion):
            return Fermion(self.operators + other.operators)

        if isinstance(other, FermionSentence):
            return FermionSentence({self: 1}) * other

        raise TypeError("invalid multiplication")

    def __rmul__(self, other):
        if isinstance(other, (int, float)):
            return FermionSentence({self: other})
        return self * other

    def __add__(self, other):
        """Promote Fermion + Fermion/FermionSentence → FermionSentence."""
        if isinstance(other, Fermion):
            return FermionSentence({self: 1}) + FermionSentence({other: 1})

        if isinstance(other, FermionSentence):
            return FermionSentence({self: 1}) + other

        return NotImplemented

    def __radd__(self, other):
        if other == 0:
            return self
        if isinstance(other, FermionSentence):
            return other + FermionSentence({self: 1})
        return self.__add__(other)

    def __sub__(self, other):
        return FermionSentence({self: 1}) - other


# ======================================================
# HIGH LEVEL API
# ======================================================

def CreateFermion(orbital: int, spin: str | None = None):
    """Create a fermionic creation operator.

    Args:
        orbital: Orbital index.
        spin: Optional spin label ("a" or "b").

    Returns:
        Fermionic creation operator.
    """
    spin = _resolve_spin(orbital, spin)
    return Fermion({(0, orbital, spin): "+"})


def AnnihilateFermion(orbital: int, spin: str | None = None):
    """Create a fermionic annihilation operator.

    Args:
        orbital: Orbital index.
        spin: Optional spin label ("a" or "b").

    Returns:
        Fermionic annihilation operator.
    """
    spin = _resolve_spin(orbital, spin)
    return Fermion({(0, orbital, spin): "-"})

def number_operator(n_orbitals: int, orbital: int | None = None):
    """Construct a fermionic number operator.

    Args:
        n_orbitals: Total number of orbitals.
        orbital: Orbital index. If None, returns the total
            number operator.

    Returns:
        Fermionic number operator as a FermionSentence.
    """
    if not isinstance(n_orbitals, int):
        raise TypeError("n_orbitals must be int")

    if n_orbitals < 0:
        raise ValueError("n_orbitals must be non-negative")

    if orbital is not None:

        if not isinstance(orbital, int):
            raise TypeError("orbital must be int")

        if orbital < 0:
            raise ValueError("orbital must be non-negative")

        if orbital >= n_orbitals:
            raise ValueError("orbital must be smaller than n_orbitals")

        term = CreateFermion(orbital) * AnnihilateFermion(orbital)

        return FermionSentence({
            term: 1
        })

    terms = {}

    for i in range(n_orbitals):
        term = CreateFermion(i) * AnnihilateFermion(i)
        terms[term] = 1

    return FermionSentence(terms)


# ======================================================
# LINEAR COMBINATION
# ======================================================

class FermionSentence(dict):
    """Linear combination of fermionic operator products."""
    def __str__(self):
        if not self:
            return "0 * I"
        return "\n+ ".join(f"{c} * {f}" for f, c in self.items())

    def __repr__(self):
        return f"FermionSentence({dict(self)})"

    def _latex_core(self) -> str:

        if not self:
            return "0"

        terms = []

        for op, coef in self.items():

            # Formatted coefficient
            if coef == 1:
                c = ""
            elif coef == -1:
                c = "-"
            else:
                c = f"{coef} "

            terms.append(f"{c}{op._latex_core()}")

        return " + ".join(terms).replace("+ -", "- ")

    def _repr_latex_(self) -> str:
        return f"${self._latex_core()}$"

    def __add__(self, other):

        if isinstance(other, Fermion):
            other = FermionSentence({other: 1})

        if not isinstance(other, FermionSentence):
            return NotImplemented

        result = copy(self)

        for k, v in other.items():
            result[k] = result.get(k, 0) + v

        return FermionSentence(result)


    def __radd__(self, other):
        if other == 0:
            return self
        return self.__add__(other)

    def __sub__(self, other):
        return self + (-1) * other

    def adjoint(self):
        """Return the Hermitian adjoint of the fermionic sentence."""

        new_terms = {}

        for term, coef in self.items():
            new_terms[term.adjoint()] = complex(coef).conjugate()

        return FermionSentence(new_terms)

    def __mul__(self, other):

        # FermionSentence * FermionSentence
        if isinstance(other, FermionSentence):

            result = FermionSentence({})

            for t1, c1 in self.items():
                for t2, c2 in other.items():
                    new_term = t1 * t2
                    result[new_term] = result.get(new_term, 0) + c1 * c2

            return result

        # FermionSentence * Fermion
        if isinstance(other, Fermion):
            return self * FermionSentence({other: 1})

        # scalar
        return FermionSentence({k: v * other for k, v in self.items()})

    __rmul__ = __mul__

    def simplify(self, tol=1e-8) -> None:
        """Remove terms with small coefficients in place."""
        items = list(self.items())
        for term, coef in items:
            if abs(coef) <= tol:
                del self[term]

    def normal_ordered(self, tol=1e-8):
        """Return the normal ordered form of the operator.

        The normal ordered form of an operator is an equivalent operator in which
        each term has been reordered into a canonical ordering. All creation
        operators appear before all annihilation operators; within creation/annihilation
        operators, spin beta operators appear before spin alpha operators, and
        larger orbital indices appear before smaller orbital indices.

        Args:
            tol: Tolerance for removing small coefficients.

        Returns:
            The normal-ordered fermion operator as a FermionSentence.
        """
        result = FermionSentence({})

        for term, coef in self.items():
            if abs(coef) < tol:
                continue

            ops = [(op.orbital, op.spin, op.action) for op in term.operators]

            def sort_term(ops_list, current_coef):
                for i in range(len(ops_list) - 1):
                    orb1, spin1, op1 = ops_list[i]
                    orb2, spin2, op2 = ops_list[i+1]

                    # Rank: + before -, 'b' before 'a', larger orb before smaller
                    def rank(orb, spin, op):
                        return (0 if op == "+" else 1, 0 if spin == "b" else 1, -orb)

                    if rank(orb1, spin1, op1) > rank(orb2, spin2, op2):
                        if (orb1, spin1) == (orb2, spin2):
                            if op1 == op2:
                                return FermionSentence({})

                            if op1 == "-" and op2 == "+":
                                new_ops_1 = ops_list[:i] + ops_list[i+2:]
                                res1 = sort_term(new_ops_1, current_coef)

                                new_ops_2 = ops_list[:]
                                new_ops_2[i], new_ops_2[i+1] = new_ops_2[i+1], new_ops_2[i]
                                res2 = sort_term(new_ops_2, -current_coef)

                                return res1 + res2

                        new_ops = ops_list[:]
                        new_ops[i], new_ops[i+1] = new_ops[i+1], new_ops[i]
                        return sort_term(new_ops, -current_coef)

                new_term = Fermion(
                    tuple(FermionOperator(orb, spin, op) for (orb, spin, op) in ops_list)
                )
                return FermionSentence({new_term: current_coef})

            result += sort_term(ops, coef)

        result.simplify(tol)
        return result

    def conserves_particle_number(self) -> bool:
        """Check whether the operator conserves particle number."""
        for term in self:

            n_creation = 0
            n_annihilation = 0

            for op in term.operators:

                if op.action == "+":
                    n_creation += 1

                elif op.action == "-":
                    n_annihilation += 1

            if n_creation != n_annihilation:
                return False

        return True

    def conserves_spin_z(self) -> bool:
        """Check whether the operator conserves the z component of spin."""
        for term in self:

            alpha_creation = 0
            alpha_annihilation = 0

            beta_creation = 0
            beta_annihilation = 0

            for op in term.operators:

                if op.spin == "a":

                    if op.action == "+":
                        alpha_creation += 1

                    elif op.action == "-":
                        alpha_annihilation += 1

                elif op.spin == "b":

                    if op.action == "+":
                        beta_creation += 1

                    elif op.action == "-":
                        beta_annihilation += 1

            if alpha_creation != alpha_annihilation:
                return False

            if beta_creation != beta_annihilation:
                return False

        return True

    def is_two_body_number_conserving(self) -> bool:
        """Check whether the operator is at most two-body and
        conserves particle number."""
        for term in self:

            n_operators = len(term)

            # allowed:
            # 0 -> identity
            # 2 -> one-body
            # 4 -> two-body
            if n_operators not in (0, 2, 4):
                return False

        return self.conserves_particle_number()
