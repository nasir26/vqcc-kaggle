/* Flip-graph search (Kauers and Moosbauer 2022) for low-rank bilinear schemes of multiplication in GF(2^n).
 *
 * Author: Nasir Ali, C-DAC Noida.
 *
 * A scheme is a list of rank-one terms (a, b, c): bit masks of linear forms on x, on y, and an output vector, with
 *   x * y = sum_t (a_t . x)(b_t . y) c_t   for all x, y in GF(2^n) (polynomial basis, given modulus).
 * Each term costs one AND in a quantum circuit, so the rank is the Toffoli count of a multiplier.
 * Moves: a flip on two terms sharing a factor keeps the rank, e.g. for a_t = a_u:
 *   a (x) b_t (x) c_t + a (x) b_u (x) c_u = a (x) (b_t + b_u) (x) c_t + a (x) b_u (x) (c_t + c_u);
 * a term with a zero factor is dropped, and two terms sharing two factors are merged (rank reductions).
 * When no reduction comes for `plateau` flips, a plus transition (rank + 1) moves to a different region.
 * Every scheme written is checked against the full multiplication tensor.
 *
 * usage: [FG_INIT=scheme.txt] flipgraph N MODULUS TARGET_RANK SEED MAX_STEPS [PLATEAU] > out.txt
 * output: one line per improvement "rank R: a,b,c a,b,c ..." (hex), verified.
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>

#define MAXM 512
static int n;
static uint32_t T[32][32];               /* T[i][j] = e_i * e_j */
static uint32_t A[MAXM], B[MAXM], C[MAXM];
static int m;
static uint64_t rng;

static uint64_t rnd(void) { rng ^= rng << 13; rng ^= rng >> 7; rng ^= rng << 17; return rng; }

static uint32_t gfmul(uint32_t a, uint32_t b, uint32_t mod) {
    uint32_t r = 0;
    while (b) { if (b & 1) r ^= a; b >>= 1; a <<= 1; if (a >> n) a ^= mod; }
    return r;
}

static int verify(void) {
    for (int i = 0; i < n; i++)
        for (int j = 0; j < n; j++) {
            uint32_t acc = 0;
            for (int t = 0; t < m; t++)
                if (((A[t] >> i) & 1) && ((B[t] >> j) & 1)) acc ^= C[t];
            if (acc != T[i][j]) return 0;
        }
    return 1;
}

static void drop(int t) { m--; A[t] = A[m]; B[t] = B[m]; C[t] = C[m]; }

/* remove zero terms and merge terms that share two factors; returns 1 if the rank changed */
static int cleanup(void) {
    int changed = 0, again = 1;
    while (again) {
        again = 0;
        for (int t = 0; t < m; t++)
            if (!A[t] || !B[t] || !C[t]) { drop(t); t--; changed = again = 1; }
        for (int t = 0; t < m && !again; t++)
            for (int u = t + 1; u < m && !again; u++) {
                if (A[t] == A[u] && B[t] == B[u]) { C[t] ^= C[u]; drop(u); again = changed = 1; }
                else if (A[t] == A[u] && C[t] == C[u]) { B[t] ^= B[u]; drop(u); again = changed = 1; }
                else if (B[t] == B[u] && C[t] == C[u]) { A[t] ^= A[u]; drop(u); again = changed = 1; }
            }
    }
    return changed;
}

/* one random flip; returns 0 if no pair shares a factor */
static int flip(void) {
    int pt[MAXM * 4], pu[MAXM * 4], pk[MAXM * 4], np = 0;
    for (int tries = 0; tries < 4 * m && np < MAXM * 4; tries++) {
        int t = rnd() % m, u = rnd() % m;
        if (t == u) continue;
        if (A[t] == A[u]) { pt[np] = t; pu[np] = u; pk[np++] = 0; }
        if (B[t] == B[u]) { pt[np] = t; pu[np] = u; pk[np++] = 1; }
        if (C[t] == C[u]) { pt[np] = t; pu[np] = u; pk[np++] = 2; }
    }
    if (!np) {  /* exhaustive fallback */
        for (int t = 0; t < m; t++)
            for (int u = 0; u < m; u++) {
                if (t == u || np >= MAXM * 4) continue;
                if (A[t] == A[u]) { pt[np] = t; pu[np] = u; pk[np++] = 0; }
                if (B[t] == B[u]) { pt[np] = t; pu[np] = u; pk[np++] = 1; }
                if (C[t] == C[u]) { pt[np] = t; pu[np] = u; pk[np++] = 2; }
            }
        if (!np) return 0;
    }
    int s = rnd() % np, t = pt[s], u = pu[s];
    switch (pk[s]) {           /* shared factor k: add u's first other factor into t's, t's second into u's */
    case 0: B[t] ^= B[u]; C[u] ^= C[t]; break;
    case 1: A[t] ^= A[u]; C[u] ^= C[t]; break;
    default: A[t] ^= A[u]; B[u] ^= B[t]; break;
    }
    return 1;
}

/* plus transition: a b c + a' b' c' = (a+a') b c + a' (b+b') c + a' b' (c+c') */
static void plus(void) {
    if (m + 1 >= MAXM) return;
    int t = rnd() % m, u = rnd() % m;
    if (t == u) return;
    uint32_t a = A[t], b = B[t], c = C[t], a2 = A[u], b2 = B[u], c2 = C[u];
    A[t] = a ^ a2; B[t] = b; C[t] = c;
    A[u] = a2; B[u] = b ^ b2; C[u] = c;
    A[m] = a2; B[m] = b2; C[m] = c ^ c2; m++;
}

static void dump(int bestm) {
    printf("rank %d:", bestm);
    for (int t = 0; t < m; t++) printf(" %x,%x,%x", A[t], B[t], C[t]);
    printf("\n");
    fflush(stdout);
}

int main(int argc, char **argv) {
    if (argc < 6) { fprintf(stderr, "usage: flipgraph N MODULUS TARGET SEED STEPS [PLATEAU]\n"); return 2; }
    n = atoi(argv[1]);
    uint32_t mod = strtoul(argv[2], 0, 0);
    int target = atoi(argv[3]);
    rng = strtoull(argv[4], 0, 0) * 0x9E3779B97F4A7C15ull + 1;
    long long steps = atoll(argv[5]);
    long long plateau = argc > 6 ? atoll(argv[6]) : 200000;
    for (int i = 0; i < n; i++)
        for (int j = 0; j < n; j++) T[i][j] = gfmul(1u << i, 1u << j, mod);
    m = 0;
    const char *init = getenv("FG_INIT");          /* start scheme: "a,b,c" hex triples, e.g. from scheme42.py */
    if (init) {
        FILE *f = fopen(init, "r");
        if (!f) { perror(init); return 1; }
        unsigned a, b, c;
        while (m < MAXM && fscanf(f, " %x,%x,%x", &a, &b, &c) == 3) { A[m] = a; B[m] = b; C[m] = c; m++; }
        fclose(f);
    } else {                                       /* trivial scheme: one term per (i, j) */
        for (int i = 0; i < n; i++)
            for (int j = 0; j < n; j++) { A[m] = 1u << i; B[m] = 1u << j; C[m] = T[i][j]; m++; }
    }
    cleanup();
    if (!verify()) { fprintf(stderr, "start scheme wrong\n"); return 1; }
    int best = m;
    long long since = 0;
    for (long long s = 0; s < steps; s++) {
        if (!flip()) { plus(); continue; }
        if (cleanup()) {
            if (m < best) {
                if (!verify()) { fprintf(stderr, "BUG: invalid scheme at rank %d\n", m); return 1; }
                best = m; dump(best); since = 0;
                if (best <= target) return 0;
            }
        }
        if (++since > plateau && m <= best + 2) { plus(); since = 0; }
        if (m > best + 6) {   /* drifted too far up: keep walking, reductions will follow */
            since = 0;
        }
    }
    fprintf(stderr, "seed %s best %d\n", argv[4], best);
    return 0;
}
