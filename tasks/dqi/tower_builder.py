"""CircuitBuilder proxy that replaces kickmix's GF(2^12) multiply / inverse / divide with tower-field
bilinear circuits (tasks/dqi/tower.py), delegating every other method to the wrapped builder.

Each rank-1 term (alpha . X)(beta . Y) -> gamma: linear forms are XOR'd into ancillas by CNOTs,
one init_and computes the product, CNOTs fan it out into the target bits, and del_and uncomputes it
by measurement. Scaffold registers are uncomputed by measurement-based uncomputation: HMR into
classical bits, then CZ(alpha . X, beta . Y) / Z(Z bit) conditioned on each outcome bit -- Clifford
only, so deletions cost zero Toffolis (the same contract as kickmix's *_with_scaffold methods).

Usage: builder = TowerBuilder(km.CircuitBuilder()); pass it wherever a CircuitBuilder is expected.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import tower  # noqa: E402


class TowerBuilder:
    def __init__(self, inner, *, modulus: int = 4179, replace_mul: bool = True, replace_inverse: bool = True):
        import kickmix as km
        self._km = km
        self._b = inner
        self._modulus = modulus
        self._mul_terms = tower.mul_terms_std(modulus)
        self._inv_steps = tower.inverse_steps(modulus)
        self._replace_mul = replace_mul
        self._replace_inverse = replace_inverse

    def __getattr__(self, name):
        return getattr(self._b, name)

    # -- helpers ----------------------------------------------------------------

    def _check_field(self, field, width: int) -> None:
        if width != 12 or (field is not None and (field.degree != 12 or field.modulus != self._modulus)):
            raise ValueError('TowerBuilder only supports km.GF2Field(12) with modulus 4179')

    def _form(self, reg, form: int):
        """Qubit holding (form . reg): the qubit itself for a single bit, else a fresh ancilla."""
        km, b = self._km, self._b
        idx = [i for i in range(len(reg)) if (form >> i) & 1]
        if len(idx) == 1:
            return reg[idx[0]], None
        anc = b.alloc_qubits(1)[0]
        b.cx(km.array([reg[i] for i in idx]), anc)
        return anc, idx

    def _unform(self, reg, anc, idx) -> None:
        if idx is not None:
            self._b.cx(self._km.array([reg[i] for i in idx]), anc)
            self._b.free(anc)

    @staticmethod
    def _bits(mask: int):
        return [i for i in range(mask.bit_length()) if (mask >> i) & 1]

    def _apply(self, terms, x, y, target, same: bool, z=None, linear=()) -> None:
        """target ^= sum_k gamma_k (alpha_k . x)(beta_k . y) + linear(z)."""
        km, b = self._km, self._b
        for t in terms:
            tgt = km.array([target[i] for i in self._bits(t.gamma)])
            fa, ia = self._form(x, t.alpha)
            if same and t.alpha == t.beta:
                b.cx(fa, tgt)
            else:
                fb, ib = self._form(y, t.beta)
                p = b.alloc_qubits(1)[0]
                b.init_and(fa, fb, p)
                b.cx(p, tgt)
                b.del_and(fa, fb, p)
                b.free(p)
                self._unform(y, fb, ib)
            self._unform(x, fa, ia)
        for j, col in enumerate(linear):
            if col:
                b.cx(z[j], km.array([target[i] for i in self._bits(col)]))

    def _unapply(self, terms, x, y, target, same: bool, z=None, linear=()) -> None:
        """Measurement-based uncomputation of a register that holds exactly the _apply value."""
        km, b = self._km, self._b
        bits = b.alloc_bits(len(target))
        b.hmr(target, bits)
        for t in terms:
            fa, ia = self._form(x, t.alpha)
            degenerate = same and t.alpha == t.beta
            if not degenerate:
                fb, ib = self._form(y, t.beta)
            for i in self._bits(t.gamma):
                b.push_condition(bits[i])
                if degenerate:
                    b.z(fa)
                else:
                    b.cz(fa, fb)
                b.pop_condition()
            if not degenerate:
                self._unform(y, fb, ib)
            self._unform(x, fa, ia)
        for j, col in enumerate(linear):
            for i in self._bits(col):
                b.push_condition(bits[i])
                b.z(z[j])
                b.pop_condition()
        b.free(bits)

    def _inverse_regs(self, inp, out, scaffold):
        D, E, F, G = scaffold[0:6], scaffold[6:9], scaffold[9:12], scaffold[12:18]
        return {'in': inp, 'D': D, 'E': E, 'F': F, 'G': G, 'out': out}

    def _run_inverse(self, inp, out, scaffold, *, delete: bool) -> None:
        regs = self._inverse_regs(inp, out, scaffold)
        steps = reversed(self._inv_steps) if delete else self._inv_steps
        for s in steps:
            args = (s.terms, regs[s.x], regs[s.y], regs[s.target], s.x == s.y,
                    regs[s.z] if s.z else None, s.linear)
            (self._unapply if delete else self._apply)(*args)

    # -- replaced kickmix methods -------------------------------------------------

    def ixor_gf2_mul(self, lhs, rhs, *, target, field=None, control=True):
        if not self._replace_mul:
            return self._b.ixor_gf2_mul(lhs, rhs, target=target, field=field, control=control)
        km, b = self._km, self._b
        self._check_field(field, len(target))
        if control is False:
            return
        if control is True:
            return self._apply(self._mul_terms, lhs, rhs, target, False)
        if isinstance(control, km.b):
            b.push_condition(control)
            self._apply(self._mul_terms, lhs, rhs, target, False)
            b.pop_condition()
            return
        masked = b.alloc_qubits(len(lhs))  # control AND lhs, uncomputed by measurement
        b.init_and(control, lhs, masked)
        self._apply(self._mul_terms, masked, rhs, target, False)
        b.del_and(control, lhs, masked)
        b.free(masked)

    def init_gf2_inverse_with_scaffold(self, input, *, target='alloc', field=None):
        if not self._replace_inverse:
            return self._b.init_gf2_inverse_with_scaffold(input, target=target, field=field)
        self._check_field(field, len(input))
        out = self._b.alloc_qubits(12) if isinstance(target, str) else target
        scaffold = self._b.alloc_qubits(18)
        self._run_inverse(input, out, scaffold, delete=False)
        return out, scaffold

    def del_gf2_inverse_with_scaffold(self, input, *, target, scaffold, field=None):
        if not self._replace_inverse:
            return self._b.del_gf2_inverse_with_scaffold(input, target=target, scaffold=scaffold, field=field)
        self._check_field(field, len(input))
        self._run_inverse(input, target, scaffold, delete=True)

    def init_gf2_div_with_scaffold(self, lhs, rhs, *, target='alloc', field=None):
        if not self._replace_inverse:
            return self._b.init_gf2_div_with_scaffold(lhs, rhs, target=target, field=field)
        self._check_field(field, len(lhs))
        inv = self._b.alloc_qubits(12)
        chain = self._b.alloc_qubits(18)
        self._run_inverse(rhs, inv, chain, delete=False)
        ratio = self._b.alloc_qubits(12) if isinstance(target, str) else target
        self._apply(self._mul_terms, lhs, inv, ratio, False)
        return ratio, inv + chain

    def del_gf2_div_with_scaffold(self, lhs, rhs, *, target, scaffold, field=None):
        if not self._replace_inverse:
            return self._b.del_gf2_div_with_scaffold(lhs, rhs, target=target, scaffold=scaffold, field=field)
        self._check_field(field, len(lhs))
        inv, chain = scaffold[:12], scaffold[12:]
        self._unapply(self._mul_terms, lhs, inv, target, False)
        self._run_inverse(rhs, inv, chain, delete=True)
