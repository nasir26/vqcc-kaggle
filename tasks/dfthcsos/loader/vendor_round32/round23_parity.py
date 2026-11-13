# SPDX-License-Identifier: Apache-2.0
"""Randomized algebraic linear matroid parity over GF(2^16).

Every returned selection is checked for exact binary independence; finite
field randomness can miss a selection, never certify a dependent one.
"""
import numpy as np,random
from round23_synthesis import bits,reduce,basis
_log=None
def tables():
 global _log,_exp
 if _log is not None:return
 _log=np.zeros(65536,dtype=np.int32);_exp=np.zeros(131070,dtype=np.uint16);x=1
 for i in range(65535):
  _exp[i]=x;_log[x]=i;x<<=1
  if x&65536:x^=0x1100b
 assert x==1 and len(np.unique(_exp[:65535]))==65535
 _exp[65535:]=_exp[:65535]
def mul(a,b):
 a=np.asarray(a,dtype=np.uint16);b=np.asarray(b,dtype=np.uint16)
 return np.where((a==0)|(b==0),0,_exp[_log[a]+_log[b]])
def inv(a):return _exp[65535-_log[a]]
def inverse(a):
 n=len(a);x=np.concatenate((a.copy(),np.eye(n,dtype=np.uint16)),axis=1)
 for i in range(n):
  nz=np.flatnonzero(x[i:,i])
  if not len(nz):return None
  j=i+int(nz[0]);x[[i,j]]=x[[j,i]];x[i]=mul(x[i],inv(x[i,i]));v=x[:,i].copy();v[i]=0;x^=mul(v[:,None],x[i][None,:])
 return x[:,n:]
def rank(a):
 x=a.copy();r=0
 for i in range(x.shape[1]):
  nz=np.flatnonzero(x[r:,i])
  if not len(nz):continue
  j=r+int(nz[0]);x[[r,j]]=x[[j,r]];x[r]=mul(x[r],inv(x[r,i]));v=x[:,i].copy();v[r]=0;x^=mul(v[:,None],x[r][None,:]);r+=1
  if r==len(x):break
 return r
def coordinates(vectors):
 piv={};original=[]
 for x in vectors:
  r=reduce(x,{k:v[0] for k,v in piv.items()})
  if not r:continue
  combo=1<<len(original);original.append(x)
  while x:
   j=x.bit_length()-1
   if j not in piv:piv[j]=(x,combo);break
   v,c=piv[j];x^=v;combo^=c
 def coord(x):
  combo=0
  while x:
   j=x.bit_length()-1;v,c=piv[j];x^=v;combo^=c
  return combo
 return original,coord
def select(pairs,singles,seed=0,allow_singles=0,extract=True):
 """Return independent original pair indices and singleton indices."""
 tables();rng=random.Random(seed);original,coord=coordinates(singles);d=len(original)
 data=[(coord(a),coord(b),i,None) for i,(a,b) in enumerate(pairs)]
 for dummy in range(allow_singles):
  for i,v in enumerate(singles):data.append((coord(v),1<<(d+dummy),None,i))
 n=d+allow_singles
 if n%2:return None,dict(feature_rank=d,dimension=n,error='odd dimension')
 ab=[(np.array(list(bits(a)),int),np.array(list(bits(b)),int)) for a,b,i,j in data]
 weights=[rng.randrange(1,65536) for x in data];mat=np.zeros((n,n),dtype=np.uint16)
 for (aa,bb),w in zip(ab,weights):
  mat[np.ix_(aa,bb)]^=w;mat[np.ix_(bb,aa)]^=w
 if not extract:
  r=rank(mat)
  return([]if r==n else None),dict(feature_rank=d,dimension=n,paired_matrix_rank=r)
 ai=inverse(mat)
 if ai is None:return None,dict(feature_rank=d,dimension=n,paired_matrix_rank=rank(mat))
 order=list(range(len(data)));rng.shuffle(order);kept=[]
 for index in order:
  aa,bb=ab[index];u=np.bitwise_xor.reduce(ai[:,aa],axis=1) if len(aa) else np.zeros(n,np.uint16);v=np.bitwise_xor.reduce(ai[:,bb],axis=1) if len(bb) else np.zeros(n,np.uint16)
  s=int(np.bitwise_xor.reduce(u[bb])) if len(bb) else 0
  det=int(mul(weights[index],s))^1
  if not det:kept.append(index);continue
  scale=mul(weights[index],inv(det));ai^=mul(scale,mul(u[:,None],v[None,:])^mul(v[:,None],u[None,:]))
 # In a generic field draw only the indispensable pairs remain.
 if len(kept)!=n//2:return None,dict(feature_rank=d,dimension=n,kept=len(kept),error='finite-field accidental retention')
 cols=[x for i in kept for x in data[i][:2]];assert len(basis(cols))==len(cols)==n
 return [(data[i][2],data[i][3]) for i in kept],dict(feature_rank=d,dimension=n,products=len(kept),singles=allow_singles)
