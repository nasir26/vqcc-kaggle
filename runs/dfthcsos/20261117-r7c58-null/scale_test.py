# [ours] product count of our planner at A=1220 vs the first A rows of the same delta table (loader scaling with A)
import sys, random, numpy as np
from multiprocessing import Pool
sys.path.insert(0,'tasks/dfthcsos/loader')
import plan_core as P
R=P.R; MP=P.MP
z=np.load(sys.argv[1]); W=z['angle_words'].astype(np.int64)
k=int(sys.argv[2]); A=int(sys.argv[3]); lo,hi=int(sys.argv[4]),int(sys.argv[5]); n=int(sys.argv[6])
B=W.reshape(-1,15,5)[:A]; D=B[:,k]^B[:,k-1]
coeff=P.anf(D)
def run(seed):
    rng=random.Random(seed)
    mons=list(range(1,16)); rng.shuffle(mons)
    groups=[tuple(mons[i:i+3]) for i in range(0,15,3)]; lay=[(rng.randint(lo,hi),) for _ in groups]
    try:
        lows,target,rep=R.prepare_layout(coeff,lay,seed,groups=groups,prefix=False)
        feats=[(a,f,R.feature(a,f)) for a,c,ns in lows for f in ns]; fs=[v for a,f,v in feats]
        if len(R.basis(fs))!=target: return None
        pairs=R.candidates(lows,seed=seed,extra=-1)
        for s in range(0,6):
            res,st=MP.select([(p[3],p[4]) for p in pairs],fs,seed*7+s,allow_singles=target%2+2*s)
            if res is not None: return (len(res),target,lay)
    except Exception:
        return None
with Pool(100) as p:
    out=[r for r in p.imap_unordered(run,range(n)) if r]
out.sort()
print('A',A,'k',k,'best',out[:3],'evaluated',len(out),flush=True)
