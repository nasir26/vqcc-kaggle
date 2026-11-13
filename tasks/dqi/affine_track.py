"""Shared affine-signature tracker for kmx dqi circuits (used by the width-cut tools).

Each qubit / classical bit value is an affine GF(2) form over atoms: (sig, cst) with sig an XOR of random W-bit
atom signatures. Products of two forms get a product atom keyed by the 2-dim subspace of their linear parts, so
equal ANDs cancel exactly. Writes under a classical condition (PUSH_CONDITION scope or 'if b' suffix on a CCX/
CSWAP) produce fresh opaque atoms; a conditional HMR/R zeroes a qubit only if it was zero at scope entry.
Conservative in the safe direction: a wire reported zero is zero for every input (up to 2^-W collisions).
"""
import random


class Tracker:
    def __init__(self, W=64, seed=7, NQ=4096, NB=400000):
        self.W = W; self.rng = random.Random(seed)
        self.sig = [0] * NQ; self.cst = [0] * NQ
        self.bsig = [0] * NB; self.bcst = [0] * NB
        self.patoms = {}; self.depth = 0; self.scope_nz = []   # stack of sets of qubits nonzero at entry
        self.section = '-'

    def R(self): return self.rng.getrandbits(self.W) | 1

    def nonzero(self, i): return bool(self.sig[i] or self.cst[i])

    def prodsig(self, sa, ca, sb, cb):
        if sa == 0: return (sb if ca else 0), ca & cb
        if sb == 0: return (sa if cb else 0), ca & cb
        if sa == sb: return (sa if (1 ^ ca ^ cb) else 0), ca & cb
        u, v, _ = sorted((sa, sb, sa ^ sb)); Wd = u ^ v
        P = self.patoms.get((u, v))
        if P is None: P = self.patoms[(u, v)] = self.R()
        s = P; pair = {sa, sb}
        if pair == {u, Wd}: s ^= u
        elif pair == {v, Wd}: s ^= v
        if cb: s ^= sa
        if ca: s ^= sb
        return s, ca & cb

    def step(self, p):
        """Apply one tokenised kmx line. Returns list of qubit indices it references (or None for meta lines)."""
        if not p: return None
        op = p[0]
        sig, cst, bsig, bcst = self.sig, self.cst, self.bsig, self.bcst
        if op == 'INFO_TAG':
            t = p[1].strip('"')
            if t.startswith('@enter:') and t[7:] in SECS: self.section = t[7:]
            return None
        if op == 'PUSH_CONDITION':
            self.depth += 1
            self.scope_nz.append({i for i in range(892) if sig[i] or cst[i]})
            return None
        if op == 'POP_CONDITION':
            self.depth -= 1; self.scope_nz.pop(); return None
        if op == 'REGISTER': return None
        if op == 'APPEND_TO_REGISTER':
            x = p[1]
            if x[0] == 'q': i = int(x[1:]); sig[i] = self.R(); cst[i] = 0
            else: bsig[int(x[1:])] = self.R()
            return None
        ifb = None
        if len(p) > 2 and p[-2] == 'if': ifb = int(p[-1][1:]); p = p[:-2]
        d = self.depth
        if op.startswith('BIT_'):
            b = int(p[1][1:])
            if d or (ifb is not None and op != 'BIT_INVERT'): bsig[b] = self.R(); bcst[b] = 0
            elif op == 'BIT_STORE0': bsig[b] = 0; bcst[b] = 0
            elif op == 'BIT_STORE1': bsig[b] = 0; bcst[b] = 1
            elif op == 'BIT_INVERT':
                if ifb is None: bcst[b] ^= 1
                else: bsig[b] ^= bsig[ifb]; bcst[b] ^= bcst[ifb]
            else: bsig[b] = self.R(); bcst[b] = 0
            return []
        qs = [int(x[1:]) for x in p[1:] if x[0] == 'q']
        if op in ('Z', 'CZ', 'CCZ', 'NEG'): return qs
        if op == 'CX':
            c, t = qs
            if d:
                if sig[c] or cst[c]: sig[t] = self.R(); cst[t] = 0
            elif ifb is not None:
                s, cc = self.prodsig(sig[c], cst[c], bsig[ifb], bcst[ifb]); sig[t] ^= s; cst[t] ^= cc
            else: sig[t] ^= sig[c]; cst[t] ^= cst[c]
        elif op == 'X':
            t = qs[0]
            if d: sig[t] = self.R(); cst[t] = 0
            elif ifb is not None: sig[t] ^= bsig[ifb]; cst[t] ^= bcst[ifb]
            else: cst[t] ^= 1
        elif op == 'CCX':
            a, b, t = qs
            if d or ifb is not None:
                if (sig[a] or cst[a]) and (sig[b] or cst[b]): sig[t] = self.R(); cst[t] = 0
            else:
                s, cc = self.prodsig(sig[a], cst[a], sig[b], cst[b]); sig[t] ^= s; cst[t] ^= cc
        elif op == 'CSWAP':
            c, a, b = qs
            if d or ifb is not None:
                for x in (a, b):
                    if sig[x] or cst[x] or sig[c] or cst[c] or sig[a] or cst[a] or sig[b] or cst[b]:
                        sig[x] = self.R(); cst[x] = 0
            else:
                s, cc = self.prodsig(sig[c], cst[c], sig[a] ^ sig[b], cst[a] ^ cst[b])
                sig[a] ^= s; cst[a] ^= cc; sig[b] ^= s; cst[b] ^= cc
        elif op == 'SWAP':
            a, b = qs
            if d or ifb is not None:
                if sig[a] or cst[a] or sig[b] or cst[b]:
                    sig[a] = self.R(); sig[b] = self.R(); cst[a] = cst[b] = 0
            else:
                sig[a], sig[b] = sig[b], sig[a]; cst[a], cst[b] = cst[b], cst[a]
        elif op in ('HMR', 'R'):
            t = qs[0]
            if (d or ifb is not None) and (t in self.scope_nz[-1] if d else True) and (sig[t] or cst[t]):
                sig[t] = self.R(); cst[t] = 0
            else:
                sig[t] = 0; cst[t] = 0
            if op == 'HMR': bsig[int(p[2][1:])] = self.R()
        else:
            raise ValueError('unknown op ' + op)
        return qs


SECS = {'mask_projection', 'initial', 'extract', 'synthesis', 'convert', 'scan', 'unconvert', 'unsynthesis',
        'unextract', 'uninitial', 'restore_masks'}
