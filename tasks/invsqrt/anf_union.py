"""Lookup synthesis estimate: 40 table outputs (cut 7180, functions of 8 address bits e,a7). Count the union of
degree>=2 ANF monomials (prefix-closed => one AND each), minimised over random invertible linear input maps and
free output basis changes are ignored (exact outputs)."""
import sys; sys.path.insert(0,'.')
import numpy as np
from kmxsim import *
c,hdr,body=load('../../data/work/invsqrt_track/base/invsqrt.kmb')
rows=[]
for e in (0,1):
    for a in range(128): rows.append(((1<<21)|(a<<14)|0x1555)>>(2+e))
xs=np.array(rows*4,dtype=np.uint64)
sim,bits=run(hdr,body,xs,62,upto=7180)
B=bits[:,:256].astype(np.uint8)
outs=[q for q in range(62) if B[q].any() and not B[q].all() and q not in range(0,14)]
F=B[outs]  # truth tables indexed by idx=e*128+a ; variables: a bits 0..6, e bit 7
def mobius(t):
    t=t.copy()
    for i in range(8):
        s=1<<i
        for j in range(256):
            if j&s: t[j]^=t[j^s]
    return t
def cost(F):
    mons=set()
    for f in F:
        an=mobius(f)
        for m in np.flatnonzero(an):
            if bin(m).count('1')>=2: mons.add(int(m))
    # prefix closure: monomial of degree d needs some degree d-1 submonomial; greedy count
    closed=set(mons)
    for m in sorted(mons,key=lambda v:-bin(v).count('1')):
        pass
    # each monomial of degree d>=2 costs 1 AND if a degree d-1 submonomial is computed; add missing
    need=set(mons); allm=set(mons)
    for d in range(8,2,-1):
        for m in [v for v in list(allm) if bin(v).count('1')==d]:
            subs=[m&~(1<<i) for i in range(8) if m>>i&1]
            if not any(s in allm for s in subs): allm.add(subs[0])
    return len(mons),len(allm)
idx=np.arange(256)
print('outputs',len(outs),'identity basis (mons, closed ANDs):',cost(F))
rng=np.random.default_rng(0); best=None
for t in range(400):
    while True:
        A=rng.integers(0,2,(8,8)).astype(np.uint8)
        if round(abs(np.linalg.det(A)))%2==1: break
    # new variable v = A*old ; f'(v)=f(A^-1 v): evaluate f at old=A^-1 v -> permute truth table
    bitsv=((idx[:,None]>>np.arange(8))&1).astype(np.uint8)
    old=(bitsv@A.T)%2  # treat as map new->old
    oi=(old<<np.arange(8)).sum(1)
    r=cost(F[:,oi])
    if best is None or r[1]<best[0]: best=(r[1],r)
print('best over 400 linear input maps:',best)
