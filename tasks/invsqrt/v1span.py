import sys; sys.path.insert(0,'.')
import numpy as np
from kmxsim import *
from probe_rot import probe
exec(open("linspan.py").read().split("if __name__")[0])
path='../../data/work/invsqrt_track/base/invsqrt.kmb'
c,hdr,body=load(path)
# reference x per (e,a) at sp=0/1 with random low bits
rng=np.random.default_rng(1)
ref=[]
for e in (0,1):
    for a in range(128):
        M=(1<<21)|(a<<14)|int(rng.integers(0,1<<14)); ref.append(M>>e)
ref=np.array(ref*2,dtype=np.uint64)
ang,P=probe(path,ref)
W=P[:15,:256].astype(np.uint8)   # stage-1 rotation bits at sp=e (normalized V1 bits, maybe shifted by 1 for e=1)
# sample x
SP=int(sys.argv[2]); xs=rng.integers(1<<(21-SP),1<<(22-SP),4000).astype(np.int64); xs=xs[xs<=X_MAX]; xs=xs[:len(xs)//64*64]
sp=21-np.floor(np.log2(xs)).astype(int); M=xs<<sp; a=(M>>14)&127; e=sp&1
key=e*128+a; assert (sp==SP).all()
T=W[:,key]
nz=[k for k in range(15) if T[k].any() and not T[k].all()]
print('nonconst V1 rows',nz)
for L in [int(v) for v in sys.argv[1].split(',')]:
    sim,bits=run(hdr,body,xs.astype(np.uint64),c.num_qubits,upto=L)
    A=np.concatenate([bits.astype(np.uint8),np.ones((1,len(xs)),np.uint8)],0)
    r0=gf2_rank(A); ok=[k for k in nz if gf2_rank(np.concatenate([A,T[k][None]],0))==r0]
    print(L,'live',int(bits.any(1).sum()),'V1 bits in span:',ok)
