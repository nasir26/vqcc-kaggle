"""Angle encoding of unit vectors on a Givens tree (inverse of the verifier's TreeMajoranaCoefficients) and rounding.

Decoding (verifier): v = e_0; for edge t = (p -> c) in order: v[p], v[c] = cos t v[p] - sin t v[c], sin t v[p] + cos t v[c],
with v[c] = 0 before its parent edge. So with A_v the amplitude arriving at v and children w_1..w_d (edge order):
A_(w_j) = r_(j-1) sin theta_j, r_j = r_(j-1) cos theta_j, u_v = r_d. Encoding takes A_w = ||u on subtree(w)|| >= 0,
r_d = u_v and walks back: r_(j-1) = sqrt(r_j^2 + A_(w_j)^2), theta_j = atan2(A_(w_j), r_j).

Word = round(theta / pi * 2^(brot - 1)) mod 2^brot.
"""
from __future__ import annotations

import numpy as np


def encode(U: np.ndarray, edges: np.ndarray) -> np.ndarray:
    """U (M, N) unit rows -> theta (M, N-1) in radians, on the tree `edges` ((N-1, 2) parent, child in order)."""
    M, N = U.shape
    children = [[] for _ in range(N)]
    for t, (p, c) in enumerate(edges):
        children[int(p)].append((t, int(c)))
    # subtree norms, post order
    order = []
    stack = [0]
    while stack:
        v = stack.pop()
        order.append(v)
        stack.extend(c for _, c in children[v])
    sq = U ** 2
    sub = sq.copy()
    for v in reversed(order):
        for _, c in children[v]:
            sub[:, v] += sub[:, c]
    # amplitude arriving at each vertex: subtree norm, signed like u_v at leaves (a leaf's value is its arrival)
    A = np.sqrt(sub)
    for v in range(N):
        if not children[v]:
            A[:, v] = U[:, v]
    theta = np.zeros((M, N - 1))
    for v in range(N):
        kids = children[v]
        if not kids:
            continue
        sgn = np.where(A[:, v] < 0, -1.0, 1.0)
        r = U[:, v].copy()  # r_d = u_v
        mag2 = U[:, v] ** 2
        for t, c in reversed(kids):
            a = A[:, c]
            mag2 = mag2 + a * a
            rp = sgn * np.sqrt(mag2)  # r_(j-1), carries the sign of the arrival A_v
            safe = np.where(rp == 0, 1.0, rp)
            theta[:, t] = np.arctan2(a / safe, r / safe)
            r = rp
    return theta


def to_words(theta: np.ndarray, brot: int) -> np.ndarray:
    s = 2 ** (brot - 1)
    return np.mod(np.rint(theta / np.pi * s).astype(np.int64), 2 ** brot)


def decode(words: np.ndarray, edges: np.ndarray, brot: int) -> np.ndarray:
    import sys, pathlib
    REPO = pathlib.Path(__file__).resolve().parents[3]
    sys.path += [str(REPO / 'data/comp/verifiers')]
    from dfthcsos.scoreinfra import dfthc_math as M
    u = M.reconstruct_u_vectors(words / 2 ** (brot - 1), edges)
    return u / np.linalg.norm(u, axis=1, keepdims=True)
