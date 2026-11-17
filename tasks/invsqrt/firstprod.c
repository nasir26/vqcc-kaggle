// ours: count L in span(B) (B = input basis incl. const) such that some h in span(B) gives L*h in span(U) but not in
// span(B). Input: file with nB, nU, then nB+nU lines "hi lo" hex (U basis = B plus targets).
#include <stdio.h>
#include <stdint.h>
#include <string.h>
typedef unsigned __int128 u128;
static int top(u128 x){ uint64_t hi=(uint64_t)(x>>64); if(hi) return 127-__builtin_clzll(hi); uint64_t lo=(uint64_t)x; return lo?63-__builtin_clzll(lo):-1; }
static u128 red(u128*p,u128 x){ while(x){int h=top(x); if(!p[h]) return x; x^=p[h];} return 0; }
static int ins(u128*p,u128 x){ x=red(p,x); if(!x) return 0; p[top(x)]=x; return 1; }
int main(int c,char**v){
  FILE*f=fopen(v[1],"r"); int nB,nU; fscanf(f,"%d %d",&nB,&nU); u128 B[64],Ub[64];
  for(int i=0;i<nB+nU;i++){ unsigned long long hi,lo; fscanf(f,"%llx %llx",&hi,&lo); u128 x=((u128)hi<<64)|lo; if(i<nB) B[i]=x; else Ub[i-nB]=x; }
  u128 PU[128]; memset(PU,0,sizeof PU); for(int i=0;i<nU;i++) ins(PU,Ub[i]);
  u128 PB[128]; memset(PB,0,sizeof PB); for(int i=0;i<nB;i++) ins(PB,B[i]);
  long good=0; uint64_t first=0;
  for(uint64_t m=1;m<(1ULL<<nB);m++){
    u128 L=0; for(int i=0;i<nB;i++) if(m>>i&1) L^=B[i];
    // residuals of L*B_i mod U, track combos
    u128 piv[128]; uint64_t pm[128]; memset(piv,0,sizeof piv);
    int found=0;
    for(int i=0;i<nB && !found;i++){
      u128 r=red(PU,L&B[i]); uint64_t mm=1ULL<<i;
      while(r){ int h=top(r); if(!piv[h]){piv[h]=r;pm[h]=mm;break;} r^=piv[h]; r=red(PU,r); mm^=pm[h]; }
      if(!r){ // combo mm gives L*h in U
        u128 h=0; for(int j=0;j<nB;j++) if(mm>>j&1) h^=B[j];
        if(red(PB,L&h)) found=1;
      }
    }
    // kernel vectors found only as they appear; also any combination of kernel vectors: check pairwise sums
    if(found){ good++; if(!first) first=m; }
  }
  printf("L with a useful first product: %ld (first mask %llx)\n",good,(unsigned long long)first); return 0; }
