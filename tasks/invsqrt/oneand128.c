// ours: does target = g ^ L*h with g,L,h in span(V u {1})?  128-bit truth tables given as two hex words "hi:lo".
// exhaustive over L in span; prints count and first masks. Usage: oneand128 TARGET V1 V2 ...
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
typedef unsigned __int128 u128;
static u128 rd(const char*s){ const char*c=strchr(s,':'); u128 hi=strtoull(s,0,16), lo=strtoull(c+1,0,16); return (hi<<64)|lo; }
static int top(u128 x){ uint64_t hi=(uint64_t)(x>>64); if(hi) return 127-__builtin_clzll(hi); uint64_t lo=(uint64_t)x; return lo?63-__builtin_clzll(lo):-1; }
static int insert(u128*b,u128 x){ while(x){int h=top(x); if(!b[h]){b[h]=x;return 1;} x^=b[h];} return 0; }
static int inspan(u128*b,u128 x){ while(x){int h=top(x); if(!b[h]) return 0; x^=b[h];} return 1; }
int main(int argc,char**argv){
  u128 v[200]; int n=0; u128 t=rd(argv[1]);
  for(int i=2;i<argc;i++) v[n++]=rd(argv[i]);
  v[n++]=~(u128)0;
  u128 B[128]; memset(B,0,sizeof B); u128 basis[128]; int r=0;
  for(int i=0;i<n;i++) if(insert(B,v[i])) basis[r++]=v[i];
  printf("rank %d\n",r);
  if(inspan(B,t)){printf("affine\n");return 0;}
  long hits=0;
  for(uint64_t m=1;m<(1ULL<<r);m++){
    u128 L=0; for(int i=0;i<r;i++) if((m>>i)&1) L^=basis[i];
    if(L==~(u128)0) continue;
    u128 C[128]; memcpy(C,B,sizeof B);
    for(int i=0;i<r;i++) insert(C,L&basis[i]);
    if(inspan(C,t)){ hits++; if(hits<3) printf("L mask %llx\n",(unsigned long long)m);}
  }
  printf("one-AND solutions: %ld\n",hits); return 0;}
