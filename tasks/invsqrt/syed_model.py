"""Standalone integer model of Syed Asad Ali's v12 invsqrt circuit (321aff83), ours.

Re-implements candidate01/whole_model.py + candidate07/oracle50.py (Apache-2.0, Syed Asad Ali) from the
pinned JSON tables, with every arithmetic parameter exposed, so that changed widths / tables / angles can be
evaluated exactly against the official tolerance on all 3,133,452 inputs.

    phase50(params) -> uint64 phase in units of 2^-50 turns (same digest as the frozen oracle for defaults)
    margin(phase50) -> exact official min margin (units 2^-64), worst ratio, argmin

Usage: python tasks/invsqrt/syed_model.py   (self-check: digest + margin of the frozen model)
"""
from __future__ import annotations

import hashlib
import json
import math
import pathlib
import sys

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[2]
SRC = REPO / 'data/src_pull/syed_v12/src_invsqrt/invsqrt_source/src/work/c10/narrow'
MODEL = json.loads((SRC / 'research/recompute_root/models/phasefit_z1_K7_G4_m37_virtual_quadS2_36_12c0.json').read_text())
_PAPER = json.loads((SRC / 'research/combined_q48_ring26/COMPLETE_GATE.json').read_text())
ANGLES50 = tuple(_PAPER['new_angles_turn_units50'])
FROZEN_SHA = '8bd482a8957cd387a2b212afdaca656947b7f89c983d67ff4eea4e14c3b0a26a'
MAX_X = 3133452
XS = np.arange(1, MAX_X + 1, dtype=np.int64)


def chart(x=XS):
    leading = np.searchsorted(np.left_shift(np.ones(22, dtype=np.int64), np.arange(22)), x, side='right') - 1
    e = (21 - leading) // 2
    norm = x << (2 * e)
    Q = np.sqrt((norm << 4).astype(np.float64)).astype(np.int64)
    Q -= (Q * Q > norm << 4)
    Q += ((Q + 1) * (Q + 1) <= norm << 4)
    v = Q - 4096
    d = 2 * Q + 1
    h = ((norm << 6) - d * d) // 64
    return dict(x=x, e=e, norm=norm, Q=Q, v=v, d=d, h=h)


def numerator_U(ch, C=None, U0=None):
    """U = U0 - F//2 (signed 15-bit product word) exactly as whole_model."""
    v, h = ch['v'], ch['h']
    C = np.asarray(MODEL['C'] if C is None else C, dtype=np.int64)[v]
    U0 = np.asarray(MODEL['U0'] if U0 is None else U0, dtype=np.int64)[v]
    q = h + 512
    F = np.zeros(len(v), dtype=np.int64)
    for i in range(10):
        shift = 8 - i
        term = (C + (1 << (shift - 1))) >> shift if shift > 0 else C if shift == 0 else 2 * C + 1
        F += (2 * ((q >> i) & 1) - 1) * term
    return U0 - F // 2


def divide(ch, U, last_row=35):
    """Non-restoring division rows j=9..last_row (whole_model); returns the 37-bit p before the exponent shift."""
    d = ch['d']
    product = U & 32767
    r = 4096 - d
    phase = np.full(len(d), -((1 << 37) - (1 << 29)), dtype=np.int64)
    for j in range(9, last_row + 1):
        sign = (r < 0).astype(np.int64)
        phase -= sign << (37 - j)
        if j <= 23:
            bit = (product >> (23 - j)) & 1
            if j == 9:
                bit = -bit
            raw = 2 * r + (2 * sign - 1) * d + bit
        elif j == 24:
            raw = 2 * r + (2 * sign - 1) * d
        else:
            k = j - 26 if j >= 28 else 0
            V = d // 2
            A = ((((V >> (k + 1)) + ((V >> k) & 1)) << (k + 1)) - (V & 1)) if k else V
            u = (r - 1) // 2
            raw = 2 * (2 * u + sign + (2 * sign - 1) * A) + 1
        nextu = raw // 2
        assert np.all((-8192 <= nextu) & (nextu < 8192)), ('overflow', j)
        nextu = ((nextu + 8192) & 16383) - 8192
        r = 2 * nextu + (raw & 1)
    phase -= (r < 0).astype(np.int64) << 1
    return (phase - 1) & ((1 << 37) - 1), r


def ring26_phase50(p, e, angles=ANGLES50):
    """oracle50: route the 27-bit word and apply the 33 refitted angles (+ Clifford/T overflow features)."""
    old = ((p << e) + (p >> (27 - e))) & ((1 << 37) - 1)
    k = e
    z = old & ((1 << 27) - 1)
    P = ((z >> k) | (z << (27 - k))) & ((1 << 27) - 1)
    W = P >> 1
    r = ((W << k) | (W >> (26 - k))) & ((1 << 26) - 1)
    direct = np.zeros(len(old), dtype=np.int64)
    for i in range(34):
        if i < 26:
            f = (r >> i) & 1
        elif i < 33:
            j = i - 26
            f = ((r >> j) & 1) * (k > j)
        else:
            f = np.ones(len(old), dtype=np.int64)
        direct += f * angles[i]
    for j in (7, 8, 9):
        direct += ((r >> j) & 1) * (k > j) * (1 << (40 + j))
    return (direct.astype(np.uint64)) & np.uint64((1 << 50) - 1), r


_REF = None


def reference():
    """Official target and tol (units 2^-64), exactly as the verifier's reference_values, cached on disk."""
    global _REF
    if _REF is None:
        cache = REPO / 'data/work/inv_gen/ref_cache.npz'
        if cache.exists():
            z = np.load(cache)
            _REF = (z['target'], z['tol'])
        else:
            num = 1 << 130
            rs = [math.isqrt(num // x) for x in range(1, MAX_X + 1)]
            target = np.array([((r + 1) >> 1) & ((1 << 64) - 1) for r in rs], dtype=np.uint64)
            tol = np.array([min(r >> 25, 1 << 63) for r in rs], dtype=np.uint64)
            cache.parent.mkdir(parents=True, exist_ok=True)
            np.savez(cache, target=target, tol=tol)
            _REF = (target, tol)
    return _REF


def margin(phase50):
    target, tol = reference()
    theta = (phase50.astype(np.uint64) << np.uint64(14))
    err = (theta - target).view(np.int64)
    used = np.abs(err).view(np.uint64)
    slack = tol.astype(np.int64) - used.astype(np.int64)
    i = int(np.argmin(slack))
    ratio = used / tol
    return dict(min_margin=int(slack[i]), argmin_x=i + 1, fail=int((slack < 0).sum()),
                worst_ratio=float(ratio.max()), worst_x=int(np.argmax(ratio)) + 1)


def rot_charge(margin_units, n_rot):
    eps = math.pi * margin_units / 2**64 / n_rot
    return n_rot * (0.56 * math.log2(1 / eps) + 5.3) / 4


def frozen():
    ch = chart()
    U = numerator_U(ch)
    p, _ = divide(ch, U)
    ph, _ = ring26_phase50(p, ch['e'])
    return ch, U, p, ph


if __name__ == '__main__':
    ch, U, p, ph = frozen()
    dig = hashlib.sha256(ph.astype('<u8').tobytes()).hexdigest()
    print('digest', dig, 'frozen match', dig == FROZEN_SHA)
    m = margin(ph)
    print(m, 'rotation charge', rot_charge(m['min_margin'], 33))
