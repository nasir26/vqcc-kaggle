"""Delta tables of the ANGLE_k loaders as GF(2) tensors T[out bit, low monomial, high block].

For loader k the circuit XORs delta[k, a] = batch[k, a] ^ batch[k-1, a] (J words of brot bits) into the word
registers. Split the address a = hi * 2^L + lo. Every Boolean function of lo is a unique XOR of monomials of the L
low bits, so delta_j(hi, lo) = XOR_mu mu(lo) G[j, mu, hi] (Moebius transform over lo). The constant monomial is free
when the high cache spans all functions of hi; the rest is a 3-tensor whose rank bounds the product count.
"""
from __future__ import annotations

import numpy as np


def batches(words: np.ndarray, J: int, brot: int) -> np.ndarray:
    """(K, A, J*brot) bits of each batch, word j bits little endian at [j*brot:(j+1)*brot]."""
    A, n = words.shape
    K = -(-n // J)
    pad = np.zeros((A, K * J), np.int64)
    pad[:, :n] = words
    b = (pad[:, :, None] >> np.arange(brot)) & 1  # (A, K*J, brot)
    return b.reshape(A, K, J * brot).transpose(1, 0, 2).astype(np.uint8)


def deltas(words, J, brot):
    b = batches(words, J, brot)
    d = b.copy()
    d[1:] ^= b[:-1]
    return d  # (K, A, bits)


def moebius(f: np.ndarray, L: int) -> np.ndarray:
    """f (..., 2^L) truth tables over lo -> ANF coefficients over monomials (bitmask index)."""
    g = f.copy()
    for i in range(L):
        s = 1 << i
        g = g.reshape(*g.shape[:-1], -1, 2 * s)
        g[..., s:] ^= g[..., :s]
        g = g.reshape(*g.shape[:-2], -1)
    return g


def tensor(delta_k: np.ndarray, L: int) -> np.ndarray:
    """delta_k (A, bits) -> T (bits, 2^L monomials, H blocks); addresses >= A are don't cares, set to 0 here."""
    A, nb = delta_k.shape
    H = -(-A // (1 << L))
    full = np.zeros((H << L, nb), np.uint8)
    full[:A] = delta_k
    f = full.reshape(H, 1 << L, nb).transpose(2, 0, 1)  # (bits, H, 2^L)
    return moebius(f, L).transpose(0, 2, 1)  # (bits, mono, H)


def gf2_rank(M: np.ndarray) -> int:
    M = (M.copy() & 1).astype(np.uint8)
    r = 0
    rows, cols = M.shape
    for c in range(cols):
        piv = np.nonzero(M[r:, c])[0]
        if len(piv) == 0:
            continue
        p = r + piv[0]
        M[[r, p]] = M[[p, r]]
        nz = np.nonzero(M[:, c])[0]
        nz = nz[nz != r]
        M[nz] ^= M[r]
        r += 1
        if r == rows:
            break
    return r
