# SPDX-License-Identifier: Apache-2.0
"""Own GF(2) low/output feature synthesis from frozen polynomial plans.

Idea lineage: mrmeows' rank-one matrix-space features; heliosli's relation
layout and shared-output pairing. This module never opens a public circuit.
"""
import itertools,random,collections

GROUPS=((1,2,4,8),(3,7,11,15),(5,6,13,14),(9,10,12))
M=35
def bits(x):
 while x:
  t=x&-x;yield t.bit_length()-1;x^=t
def reduce(x,p):
 while x:
  j=x.bit_length()-1
  if j not in p:break
  x^=p[j]
 return x
def basis(xs):
 p={}
 for x in xs:
  x=reduce(x,p)
  if x:p[x.bit_length()-1]=x
 return p
def null(xs,n):
 p=basis(xs)
 for j in sorted(p):
  for k in p:
   if k>j and p[k]>>j&1:p[k]^=p[j]
 return [(1<<k)|sum(1<<j for j in p if p[j]>>k&1) for k in range(n) if k not in p]
def compress(x):return sum((x>>(8*j)&127)<<(7*j) for j in range(5))
def expand(x):
 out=0
 for j in range(5):
  w=x>>(7*j)&127;out|=(w|((w&64)<<1))<<(8*j)
 return out
def feature(low,out):return sum(out<<(35*i) for i in bits(low))
def prepare(coeff,counts,groups=GROUPS,planes=False,seed=0):
 lows=[];report=[];total=0
 for g,count in zip(groups,counts):
  rows=[sum(compress(coeff[(h<<4)|m] if (h<<4)|m<len(coeff) else 0)<<(35*i) for i,m in enumerate(g)) for h in range(1,77)]
  allrel=null(rows,35*len(g))
  if not planes:rels=allrel[:count]
  else:
   # Build annihilators on two overlapping three-dimensional low planes.
   # Their kernels preserve generous output spaces in the omitted directions.
   rng=random.Random(seed);rels=[]
   subsets=[tuple(range(len(g)))] if len(g)<=3 or tuple(g)==GROUPS[0] else [(0,1,2),(0,1,3)]
   for sub in subsets:
    smallrows=[sum((row>>(35*i)&((1<<35)-1))<<(35*j) for j,i in enumerate(sub)) for row in rows]
    candidates=null(smallrows,35*len(sub));zeros=[x for x in candidates if x.bit_count()==1];other=[x for x in candidates if x.bit_count()!=1]
    choose=other[:count] if seed==0 else []
    if seed:
     piv={}
     while len(choose)<min(count,len(other)):
      x=0
      for r in other:
       if rng.getrandbits(1):x^=r
      rr=reduce(x,piv)
      if rr:piv[rr.bit_length()-1]=rr;choose.append(x)
    for r in zeros+choose:
     rels.append(sum((r>>(35*j)&((1<<35)-1))<<(35*i) for j,i in enumerate(sub)))
   rels=list(basis(rels).values())
  count=len(rels)
  report.append(dict(group=g,relations=count,available=len(allrel),target=35*len(g)-count));total+=35*len(g)-count
  for local in range(1,1<<len(g)):
   low=sum(1<<(m-1) for i,m in enumerate(g) if local>>i&1)
   constraints=[]
   for r in rels:
    c=0
    for i in bits(local):c^=r>>(35*i)&((1<<35)-1)
    constraints.append(c)
   lows.append((low,constraints,null(constraints,35)))
 return lows,total,report
def candidates(lows,seed=0,extra=2):
 rng=random.Random(seed);pairs=[];seen=set()
 for (a,ca,ka),(b,cb,kb) in itertools.combinations(lows,2):
  ns=null(ca+cb,35)
  fs=list(ns)
  if extra<0:fs.extend(x^y for x,y in itertools.combinations(ns,2))
  for j in range(max(0,extra)):
   f=0
   for x in ns:
    if rng.getrandbits(1):f^=x
   if f:fs.append(f)
  for f in fs:
   key=(a,b,f)
   if key not in seen:seen.add(key);pairs.append((a,b,f,feature(a,f),feature(b,f)))
 return pairs
def choose(lows,pairs,target,seed):
 rng=random.Random(seed);order=list(range(len(pairs)));rng.shuffle(order);p={};selected=[]
 for i in order:
  a,b,f,x,y=pairs[i];rx=reduce(x,p)
  if not rx:continue
  trial=dict(p);trial[rx.bit_length()-1]=rx;ry=reduce(y,trial)
  if ry:
   p=trial;p[ry.bit_length()-1]=ry
   selected.extend(((a,f,x),(b,f,y)))
   if len(p)==target:break
 paired=len(selected)
 # Complete the rank-one span with unpaired features; later group by f.
 for a,cs,ns in lows:
  for f in ns:
   x=feature(a,f);r=reduce(x,p)
   if r:p[r.bit_length()-1]=r;selected.append((a,f,x))
 assert len(p)<=target
 if len(p)!=target:return None,dict(rank=len(p),target=target,paired=paired,candidates=len(pairs))
 counts=collections.Counter(f for a,f,x in selected);cost=sum((n+1)//2 for n in counts.values())
 return selected,dict(rank=len(p),target=target,paired=paired,candidates=len(pairs),products=cost,singles=sum(n%2 for n in counts.values()))
def solve(selected,coeff,prefix=False):
 p={}
 for i,(a,f,x) in enumerate(selected):
  combo=1<<i
  while x:
   j=x.bit_length()-1
   if j not in p:p[j]=(x,combo);break
   v,c=p[j];x^=v;combo^=c
  assert x
 high=[0]*len(selected)
 for h in range(1,77):
  x=sum(compress(coeff[(h<<4)|m] if (h<<4)|m<len(coeff) else 0)<<(35*(m-1)) for m in range(1,16));combo=0
  use=p
  if prefix and h==76:
   # Only low addresses 0..3 exist in the last high block. Its other
   # twelve mixed coefficients are free completion variables.
   use={};mask=(1<<(3*35))-1;x&=mask
   for i,(a,f,v) in enumerate(selected):
    value=v&mask;co=1<<i
    while value:
     j=value.bit_length()-1
     if j not in use:use[j]=(value,co);break
     vv,cc=use[j];value^=vv;co^=cc
  while x:
   j=x.bit_length()-1
   if j not in use:raise ValueError('target outside feature span')
   v,c=use[j];x^=v;combo^=c
  for i in bits(combo):high[i]|=1<<h
 return high
def products_from(selected,high,A):
 grouped=collections.defaultdict(list)
 for (low,f,x),h in zip(selected,high):
  if h:grouped[f].append((low<<1,h))
 products=[]
 for f,items in sorted(grouped.items()):
  for i in range(0,len(items),2):
   l1,r1=items[i];l2,r2=items[i+1] if i+1<len(items) else (0,0)
   products.append(A.Product(l1,r1,l2,r2,expand(f)))
 return products
def repair_pure(plan,products,A):
 pure=dict(plan.pure)
 for p in list(plan.products)+list(products):
  for m in bits(A.poly_product(p.left1,p.left2,15)):pure[m]=pure.get(m,0)^p.fanout
  for h in bits(A.poly_product(p.right1,p.right2,76)):
   m=h<<4;pure[m]=pure.get(m,0)^p.fanout
 return {m:f for m,f in pure.items() if f}

def prepare_layout(coeff,layout,seed,groups=GROUPS,prefix=False,coordinate=False):
 """Relations on two low hyperplanes plus a residual whole-block space."""
 rng=random.Random(seed);lows=[];report=[];target=0
 for g,counts in zip(groups,layout):
  n=len(g);rows=[sum(compress(coeff[(h<<4)|m] if (h<<4)|m<len(coeff) else 0)<<(35*i) for i,m in enumerate(g)) for h in range(1,76 if prefix else 77)]
  zeros=[1<<j for j in range(35*n) if not any(row>>j&1 for row in rows)];rels=list(zeros);piv=basis(rels)
  subs=[null([(1<<n)-2],n),null([(1<<n)-1],n),[1<<i for i in range(n)]] if n>=4 else [[1<<i for i in range(n)]]
  for sub,count in zip(subs,counts):
   smallrows=[]
   for row in rows:
    r=0
    for j,b in enumerate(sub):
     out=0
     for i in bits(b):out^=row>>(35*i)&((1<<35)-1)
     r|=out<<(35*j)
    smallrows.append(r)
   ns=null(smallrows,35*len(sub));available=[]
   for r in ns:
    emb=0
    for j,b in enumerate(sub):
     out=r>>(35*j)&((1<<35)-1)
     for i in bits(b):emb^=out<<(35*i)
    if reduce(emb,piv):available.append(emb)
   # Randomized combinations avoid treating an RREF prefix as a layout.
   added=0;attempt=0
   while added<count:
    attempt+=1
    if attempt>10000:raise ValueError('layout relations exhausted')
    x=0
    if coordinate and seed:x=rng.choice(available)
    elif seed==0 and attempt<=len(available):x=available[attempt-1]
    else:
     for r in available:
      if rng.getrandbits(1):x^=r
    v=reduce(x,piv)
    if v:piv[v.bit_length()-1]=v;rels.append(x);added+=1
  report.append(dict(group=g,zero_relations=len(zeros),layout=list(counts),relations=len(rels),target=35*n-len(rels)));target+=35*n-len(rels)
  for local in range(1,1<<n):
   low=sum(1<<(m-1) for i,m in enumerate(g) if local>>i&1);cs=[]
   for r in rels:
    c=0
    for i in bits(local):c^=r>>(35*i)&((1<<35)-1)
    cs.append(c)
   lows.append((low,cs,null(cs,35)))
 return lows,target,report
