"""Block-model loader planner on top of the vendored public round32 synthesis (Apache-2.0, see vendor_round32/).

Target: ANF coefficients of the delta table D_k over address monomials S < A (40-bit packed, word j bits at 8j..8j+7),
compressed to 35 bits (bits 0..6 of each word; bit 7 is handled by the pi-gauge helper slot). Features are rank-one
matrices low (x) f (low: combination of the 15 nonconstant low monomials, f: 35-bit output vector); products pair two
features with the same f. Lows are restricted to groups of low monomials; per group a set of relations (annihilators
of the group's projection of the hi-monomial span) cuts out the feature space.
"""
from __future__ import annotations

import pathlib
import random
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / 'vendor_round32'))
import round23_synthesis as R  # noqa: E402
import round23_parity as MP  # noqa: E402


def anf(delta: np.ndarray, brot: int = 8) -> list[int]:
    a, j = delta.shape
    out = [sum(int(delta[i, w]) << (w * brot) for w in range(j)) for i in range(a)]
    for b in range((a - 1).bit_length()):
        bit = 1 << b
        for mask in range(a):
            if mask & bit:
                out[mask] ^= out[mask ^ bit]
    return out


def group_rows(coeff, g, A):
    H = (A - 1) >> 4  # last (prefix) block index; rows for h=1..H-1 are complete
    return [sum(R.compress(coeff[(h << 4) | m] if (h << 4) | m < A else 0) << (35 * i) for i, m in enumerate(g))
            for h in range(1, H)]


def prepare_random(coeff, groups, counts, rng, A):
    lows, target, rep = [], 0, []
    for g, cnt in zip(groups, counts):
        ns = R.null(group_rows(coeff, g, A), 35 * len(g))
        rels, piv = [], {}
        cnt = min(cnt, len(ns))
        while len(rels) < cnt:
            x = 0
            for r in ns:
                if rng.getrandbits(1):
                    x ^= r
            v = R.reduce(x, piv)
            if v:
                piv[v.bit_length() - 1] = v
                rels.append(x)
        target += 35 * len(g) - len(rels)
        rep.append((len(g), len(ns), len(rels)))
        for local in range(1, 1 << len(g)):
            low = sum(1 << (m - 1) for i, m in enumerate(g) if local >> i & 1)
            cs = []
            for r in rels:
                c = 0
                for i in R.bits(local):
                    c ^= r >> (35 * i) & ((1 << 35) - 1)
                cs.append(c)
            lows.append((low, cs, R.null(cs, 35)))
    return lows, target, rep


def plan_products(lows, target, seed):
    features = [(a, f, R.feature(a, f)) for a, c, ns in lows for f in ns]
    fs = [v for a, f, v in features]
    if len(R.basis(fs)) != target:
        return None, dict(error='features do not span', rank=len(R.basis(fs)), target=target)
    pairs = R.candidates(lows, seed=seed, extra=-1)
    res, st = None, None
    for att in range(3):
        res, st = MP.select([(p[3], p[4]) for p in pairs], fs, seed + att * 1000003, allow_singles=target % 2)
        if res is not None:
            break
    if res is None:
        return None, dict(error='parity failed', **(st or {}))
    sel = []
    for pi, si in res:
        if pi is None:
            sel.append(features[si])
        else:
            a, b, f, x, y = pairs[pi]
            sel.extend(((a, f, x), (b, f, y)))
    return sel, dict(products=len(res), pairs=len(pairs), target=target)
