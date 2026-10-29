/* Symmetry-restricted flip-graph search for GF(2^n) multiplication schemes (normal basis, Frobenius orbits).
 *
 * Author: Nasir Ali, C-DAC Noida.
 *
 * In a normal basis {beta^(2^i)} the Frobenius map x -> x^2 is a cyclic shift of coordinates, so rotating the
 * three masks (a, b, c) of every rank-one term of a valid scheme by the same amount gives a valid scheme. This
 * search keeps the scheme invariant under rotation by r bits (a subgroup of order n / r of the Galois group) and
 * applies every flip, plus transition and merge to whole orbits at once, then re-checks the full multiplication
 * tensor and the invariance; a move that breaks either is undone. Lower ranks reached here are converted to the
 * polynomial basis by tasks/dqi/sym_convert.py (rank is basis independent).
 *
 * usage: flipsym N MODULUS ROT SEED MAX_STEPS [PLATEAU] [TARGET]
 *   prints the normal basis element and then "rank R: a,b,c ..." (normal-basis hex masks) at each improvement.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAXM 1024
static int n, rot;
static uint32_t mask_n;
static uint32_t T[32][32];
static uint32_t A[MAXM], B[MAXM], C[MAXM];
static int m;
static uint64_t rng;

static uint64_t rnd(void) { rng ^= rng << 13; rng ^= rng >> 7; rng ^= rng << 17; return rng; }
static uint32_t gfmul(uint32_t a, uint32_t b, uint32_t mod) {
    uint32_t r = 0;
    while (b) { if (b & 1) r ^= a; b >>= 1; a <<= 1; if (a >> n) a ^= mod; }
    return r;
}
static uint32_t rotl(uint32_t v, int k) { k %= n; return ((v << k) | (v >> (n - k))) & mask_n; }

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

static int find(uint32_t a, uint32_t b, uint32_t c, const char *used) {
    for (int t = 0; t < m; t++)
        if (!used[t] && A[t] == a && B[t] == b && C[t] == c) return t;
    return -1;
}

/* every term's rotation by `rot` is in the scheme, with multiplicity */
static int invariant(void) {
    static char used[MAXM];
    memset(used, 0, m);
    for (int t = 0; t < m; t++) {
        int u = find(rotl(A[t], rot), rotl(B[t], rot), rotl(C[t], rot), used);
        if (u < 0) return 0;
        used[u] = 1;
    }
    return 1;
}

static void drop(int t) { m--; A[t] = A[m]; B[t] = B[m]; C[t] = C[m]; }

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

static uint32_t SA[MAXM], SB[MAXM], SC[MAXM];
static int sm;
static void save(void) { memcpy(SA, A, m * 4); memcpy(SB, B, m * 4); memcpy(SC, C, m * 4); sm = m; }
static void restore(void) { memcpy(A, SA, sm * 4); memcpy(B, SB, sm * 4); memcpy(C, SC, sm * 4); m = sm; }

/* flip the pair (t, u) and all its rotations; returns 0 if no move was made */
static int orbit_flip(void) {
    int t = rnd() % m, u = rnd() % m;
    if (t == u) return 0;
    int k;
    if (A[t] == A[u]) k = 0; else if (B[t] == B[u]) k = 1; else if (C[t] == C[u]) k = 2; else return 0;
    uint32_t ta = A[t], tb = B[t], tc = C[t], ua = A[u], ub = B[u], uc = C[u];
    int order = n / rot;
    for (int s = 0; s < order; s++) {
        int r = s * rot;
        static char used[MAXM];
        memset(used, 0, m);
        int ti = find(rotl(ta, r), rotl(tb, r), rotl(tc, r), used);
        if (ti < 0) return -1;
        used[ti] = 1;
        int ui = find(rotl(ua, r), rotl(ub, r), rotl(uc, r), used);
        if (ui < 0) return -1;
        switch (k) {
        case 0: B[ti] ^= B[ui]; C[ui] ^= C[ti]; break;
        case 1: A[ti] ^= A[ui]; C[ui] ^= C[ti]; break;
        default: A[ti] ^= A[ui]; B[ui] ^= B[ti]; break;
        }
    }
    return 1;
}

/* plus transition on a pair and all its rotations (rank + orbit size) */
static void orbit_plus(void) {
    int t = rnd() % m, u = rnd() % m;
    if (t == u) return;
    uint32_t ta = A[t], tb = B[t], tc = C[t], ua = A[u], ub = B[u], uc = C[u];
    int order = n / rot;
    for (int s = 0; s < order && m + 1 < MAXM; s++) {
        int r = s * rot;
        static char used[MAXM];
        memset(used, 0, m);
        int ti = find(rotl(ta, r), rotl(tb, r), rotl(tc, r), used);
        if (ti < 0) return;
        used[ti] = 1;
        int ui = find(rotl(ua, r), rotl(ub, r), rotl(uc, r), used);
        if (ui < 0) return;
        uint32_t a = A[ti], b = B[ti], c = C[ti], a2 = A[ui], b2 = B[ui], c2 = C[ui];
        A[ti] = a ^ a2;                       /* a b c + a' b' c' = (a+a') b c + a' (b+b') c + a' b' (c+c') */
        A[ui] = a2; B[ui] = b ^ b2; C[ui] = c;
        A[m] = a2; B[m] = b2; C[m] = c ^ c2; m++;
    }
}

int main(int argc, char **argv) {
    if (argc < 6) { fprintf(stderr, "usage: flipsym N MODULUS ROT SEED STEPS [PLATEAU] [TARGET]\n"); return 2; }
    n = atoi(argv[1]);
    uint32_t mod = strtoul(argv[2], 0, 0);
    rot = atoi(argv[3]);
    rng = strtoull(argv[4], 0, 0) * 0x9E3779B97F4A7C15ull + 7;
    long long steps = atoll(argv[5]);
    long long plateau = argc > 6 ? atoll(argv[6]) : 20000;
    int target = argc > 7 ? atoi(argv[7]) : 0;
    mask_n = (n == 32) ? 0xffffffffu : ((1u << n) - 1);
    if (n % rot) { fprintf(stderr, "ROT must divide N\n"); return 2; }
    /* normal basis: beta whose conjugates are linearly independent */
    uint32_t beta = 0, conj[32];
    for (uint32_t cand = 1; cand < (1u << n) && !beta; cand++) {
        uint32_t rows[32]; int rank = 0;
        uint32_t v = cand;
        for (int i = 0; i < n; i++) { conj[i] = v; v = gfmul(v, v, mod); }
        for (int i = 0; i < n; i++) {
            uint32_t x = conj[i];
            for (int r = 0; r < rank; r++) if ((x ^ rows[r]) < x) x ^= rows[r];
            if (x) { rows[rank++] = x;
                for (int a = rank - 1; a > 0 && rows[a] > rows[a - 1]; a--) { uint32_t tmp = rows[a]; rows[a] = rows[a - 1]; rows[a - 1] = tmp; } }
        }
        if (rank == n) beta = cand;
    }
    uint32_t v = beta;
    for (int i = 0; i < n; i++) { conj[i] = v; v = gfmul(v, v, mod); }
    /* coordinates in the normal basis: solve by Gaussian elimination on the conjugates */
    uint32_t M[32];  /* M[i] = conj[i] as polynomial-basis vector; need inverse map poly -> normal coords */
    uint32_t aug[32];
    for (int i = 0; i < n; i++) { M[i] = 0; }
    /* build matrix with columns conj[i]; invert: rows over poly bits */
    uint32_t rowsP[32], rowsI[32];
    for (int r = 0; r < n; r++) {
        rowsP[r] = 0;
        for (int i = 0; i < n; i++) if ((conj[i] >> r) & 1) rowsP[r] |= 1u << i;
        rowsI[r] = 1u << r;
    }
    for (int c = 0; c < n; c++) {
        int p = c; while (p < n && !((rowsP[p] >> c) & 1)) p++;
        if (p == n) { fprintf(stderr, "singular\n"); return 1; }
        uint32_t t1 = rowsP[c]; rowsP[c] = rowsP[p]; rowsP[p] = t1;
        t1 = rowsI[c]; rowsI[c] = rowsI[p]; rowsI[p] = t1;
        for (int r = 0; r < n; r++) if (r != c && ((rowsP[r] >> c) & 1)) { rowsP[r] ^= rowsP[c]; rowsI[r] ^= rowsI[c]; }
    }
    /* rowsI[i] = row i of inverse: normal coordinate i = parity(rowsI[i] & poly vector) */
    (void)M; (void)aug;
    for (int i = 0; i < n; i++)
        for (int j = 0; j < n; j++) {
            uint32_t p = gfmul(conj[i], conj[j], mod), coords = 0;
            for (int k = 0; k < n; k++) coords |= (uint32_t)(__builtin_parity(rowsI[k] & p)) << k;
            T[i][j] = coords;
        }
    printf("beta %x\n", beta);
    m = 0;
    for (int i = 0; i < n; i++)
        for (int j = 0; j < n; j++) { A[m] = 1u << i; B[m] = 1u << j; C[m] = T[i][j]; m++; }
    cleanup();
    if (!verify() || !invariant()) { fprintf(stderr, "start scheme invalid\n"); return 1; }
    int best = m;
    long long since = 0;
    for (long long s = 0; s < steps; s++) {
        save();
        int r = orbit_flip();
        if (r == 0) { if (++since > plateau) { orbit_plus(); since = 0; if (!verify() || !invariant()) restore(); } continue; }
        if (r < 0) { restore(); continue; }
        cleanup();
        if (!invariant() || !verify()) { restore(); continue; }
        if (m < best) {
            best = m; since = 0;
            printf("rank %d:", m);
            for (int t = 0; t < m; t++) printf(" %x,%x,%x", A[t], B[t], C[t]);
            printf("\n"); fflush(stdout);
            if (best <= target) return 0;
        } else if (++since > plateau && m <= best + 2 * (n / rot)) {
            orbit_plus(); since = 0;
            if (!verify() || !invariant()) restore();
        }
    }
    fprintf(stderr, "best %d\n", best);
    return 0;
}
