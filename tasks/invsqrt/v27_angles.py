"""Angle editing for the 44-qubit invsqrt (efd84ca5 lineage), ours.

sites: the 33 non-Clifford Z_POW lines of the kmx, ordered by angle magnitude (data/work/inv_gen/v27/efd_sites64.json
gives body lines; kmx line = body line + OFFSET). write_kmx(src, dst, angles64) rewrites those 33 lines with exact
dyadic decimals (units of 2^-64 turn = half_turn * 2^63).
"""
import json
from fractions import Fraction
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
V27 = REPO / 'data/work/inv_gen/v27'


def half_turn_str(u64):
    u = u64 % (1 << 64)
    if u == 0:
        return '0'
    # half turns = u / 2^63 in [0, 2)
    num = u * 5**63
    s = str(num).rjust(64, '0')
    ip, fp = s[:-63].lstrip('0') or '0', s[-63:].rstrip('0')
    return ip + ('.' + fp if fp else '')


def sites(kmx):
    lines = Path(kmx).read_text().split('\n')
    rot = []
    for i, l in enumerate(lines):
        if l.startswith('Z_POW '):
            _, q, h = l.split()
            u = Fraction(h) * 2**63
            assert u.denominator == 1
            u = int(u)
            if u % (1 << 61):
                rot.append((u, i, q))
    rot.sort()
    assert len(rot) == 33, len(rot)
    return lines, rot


def write_kmx(src, dst, angles64):
    lines, rot = sites(src)
    for (u, i, q), a in zip(rot, angles64):
        assert Fraction(half_turn_str(a)) * 2**63 == a % (1 << 64)
        lines[i] = f'Z_POW {q} {half_turn_str(a)}'
    Path(dst).write_text('\n'.join(lines))
    return [u for u, _, _ in rot]
