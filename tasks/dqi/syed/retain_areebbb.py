# Vendored verbatim from areebbb notebook qai-fewer-toffolis-same-qubits-lb-27-08903 (Apache-2.0), cell 4.
import random, collections, bisect

def read_registers(path):
    regq = set()
    with open(path) as f:
        for line in f:
            if line[0] == 'A':
                p = line.split()
                if p[1][0] == 'q': regq.add(p[1])
    return regq

def scan(path, regq, seed=20261112):
    """Forward pass with value fingerprints. Returns
    occ : product fingerprint -> [(line, a, b, t)] for unconditional top-level CCX gates
    idle: qubit -> [(z, L)] maximal windows in which the qubit is provably |0> and untouched (after line z, before line L)
    nlines"""
    rnd = random.Random(seed).getrandbits
    ONE = 1 << 64; LOW = ONE - 1
    h = collections.defaultdict(int)
    for q in regq: h[q] = rnd(64)
    memo = {}; occ = collections.defaultdict(list); idle = collections.defaultdict(list)
    zs = {}                      # qubit -> line after which it has been zero and untouched (top level only)
    seen = set()
    depth = 0; written = []; block_start = [0]
    def AND(x, y):
        xn, x0, yn, y0 = x >> 64, x & LOW, y >> 64, y & LOW
        if x0 == 0 or y0 == 0 or x0 == y0:
            core = x0 if (x0 == y0) else 0; free = True
        else:
            k = (x0, y0) if x0 < y0 else (y0, x0)
            core = memo.get(k)
            if core is None: core = memo[k] = rnd(64)
            free = False
        return core ^ (y0 if xn else 0) ^ (x0 if yn else 0) ^ (ONE if (xn and yn) else 0), free
    def touch(q, L):
        z = zs.pop(q, None)
        if z is not None:
            ins = (L - 1) if depth == 0 else (block_start[0] - 1)      # last top-level point before the touch
            if ins >= z: idle[q].append((z, L, ins))
    def settle(q, L):            # after an unconditional top-level op on q
        if depth == 0 and h[q] == 0 and q not in regq: zs[q] = L
        if written: written[-1].add(q)
    lineno = -1
    with open(path) as f:
        for lineno, line in enumerate(f):
            c0 = line[0]
            if c0 == 'C' and line[1] == 'X':
                p = line.split()
                if len(p) == 3:
                    a = p[1]; b = p[2]
                    if a in zs: touch(a, lineno); zs[a] = lineno
                    if b in zs: touch(b, lineno)
                    v = h[b] ^ h[a]; h[b] = v
                    if depth == 0:
                        if not v and b not in regq: zs[b] = lineno
                    else: written[-1].add(b)
                    continue
            p = line.split()
            if not p: continue
            op = p[0]
            if op in ('INFO_TAG', 'APPEND_TO_REGISTER', 'REGISTER', 'DEBUG_PRINT', 'BIT_INVERT', 'BIT_STORE0', 'BIT_STORE1', 'NEG'): continue
            if op == 'PUSH_CONDITION':
                if depth == 0: block_start[0] = lineno
                depth += 1; written.append(set()); continue
            if op == 'POP_CONDITION':
                if depth:
                    depth -= 1; w = written.pop()
                    for q in w: h[q] = rnd(64); zs.pop(q, None)
                    if written: written[-1] |= w
                continue
            cond = None
            if len(p) >= 3 and p[-2] == 'if': cond = p[-1]; p = p[:-2]
            qs = [t for t in p[1:] if t[0] == 'q']
            zero_before = {q: (q in zs) for q in qs}
            for q in qs: touch(q, lineno)
            if op in ('Z', 'CZ', 'CCZ', 'Z_POW'):
                if cond is None and depth == 0:
                    for q in qs:
                        if zero_before[q]: zs[q] = lineno          # phase gates leave |0> untouched in value; start a new window
                continue
            if cond is not None:
                for q in (qs[-1:] if op in ('X', 'CX', 'CCX', 'HMR', 'R') else qs if op in ('SWAP',) else qs[1:]):
                    h[q] = rnd(64)
                    if written: written[-1].add(q)
                for q in qs:
                    if zero_before[q] and h[q] == 0 and depth == 0: zs[q] = lineno
                continue
            if op == 'X': t = qs[0]; h[t] ^= ONE; settle(t, lineno)
            elif op == 'CX':
                h[qs[1]] ^= h[qs[0]]; settle(qs[1], lineno); settle(qs[0], lineno)
            elif op == 'SWAP':
                a, b = qs; h[a], h[b] = h[b], h[a]; settle(a, lineno); settle(b, lineno)
            elif op in ('R', 'HMR'):
                t = qs[0]; h[t] = 0; settle(t, lineno)
            elif op == 'CCX':
                a, b, t = qs
                P, free = AND(h[a], h[b])
                if not free and P and depth == 0: occ[P].append((lineno, a, b, t))
                h[t] ^= P; settle(t, lineno); settle(a, lineno); settle(b, lineno)
            elif op == 'CSWAP':
                c, a, b = qs
                P, free = AND(h[c], h[a] ^ h[b]); h[a] ^= P; h[b] ^= P
                for q in qs: settle(q, lineno)
            else:
                for q in qs:
                    h[q] = rnd(64)
                    if written: written[-1].add(q)
    n = lineno + 1
    for q, z in zs.items():
        if n - 1 >= z: idle[q].append((z, n, n - 1))
    return occ, idle, n

def plan(occ, idle, first_new_bit, n_lines=0, extra=(), max_span=None, max_hops=0):
    """Hold each repeated product in qubits that are provably |0> and untouched between two of its occurrences.
    A host can serve many products one after another; with max_hops > 0 a product may also move from one host to
    another (CX h g; CX g h, with g = 0) when its current host is needed again. Returns (repl, post, stats)."""
    wins = {q: sorted(ws) for q, ws in idle.items()}           # (z, L, ins): zero after line z, untouched before L, last insertion point ins
    for q in extra: wins[q] = [(-1, n_lines + 1, n_lines)]
    xs = set(extra)
    starts = {q: [w[0] for w in ws] for q, ws in wins.items()}
    busy = {q: [] for q in wins}
    def win_at(q, x):                                           # window of q with z < x... qubit zero just after line x-? : need z <= x < L
        i = bisect.bisect_right(starts[q], x) - 1
        if i < 0: return None
        w = wins[q][i]
        return w if x < w[1] else None
    def next_busy(q, x):
        b = busy[q]; i = bisect.bisect_right(b, (x, 1 << 62))
        if i > 0 and b[i - 1][1] >= x: return x - 1            # occupied at x
        return b[i][0] if i < len(b) else 1 << 62
    def reach(q, x):
        """from insertion point x (after line x), how long q can hold: (last line it may still hold through, last hop point)"""
        w = win_at(q, x)
        if w is None: return None
        nb = next_busy(q, x + 1)
        if nb <= x: return None
        hold_end = min(w[1] - 1, nb - 1)                       # holds the value through line hold_end
        hop_pt = min(w[2], nb - 1, w[1] - 1)                   # last insertion point (after that line) on q
        return hold_end, hop_pt
    pairs = []
    for P, lst in occ.items():
        for k in range(len(lst) - 1):
            st, en = lst[k][0], lst[k + 1][0]
            if max_span is None or en - st <= max_span: pairs.append((en, st, P, k))
    pairs.sort()
    host_path = {}; on_extra = 0; post = collections.defaultdict(list); nhops = 0
    for en, st, P, k in pairs:
        # first host: written at line st (the CCX itself), so it must be zero at st: window with z < st, i.e. win_at(q, st-1)
        best = None
        for q in wins:
            r = reach(q, st - 1)
            if r is None: continue
            done = r[0] >= en
            if not done and max_hops == 0: continue
            key = (done, -(q in xs), -(r[0]) if done else r[0])
            if best is None or key > best[0]: best = (key, q, r)
        if best is None: continue
        path = [(best[1], st)]; segs = []; cur, (hold_end, hop_pt) = best[1], best[2]; seg_start = st; ok = hold_end >= en
        while not ok and len(segs) < max_hops:
            if hop_pt < seg_start: break
            cand = None
            for g in wins:
                if g == cur: continue
                r = reach(g, hop_pt)
                if r is None: continue
                key = (r[0] >= en, -(g in xs), -(r[0]) if r[0] >= en else r[0])
                if r[0] <= hold_end and r[0] < en: continue
                if cand is None or key > cand[0]: cand = (key, g, r)
            if cand is None: break
            segs.append((cur, seg_start, hop_pt)); seg_start = hop_pt; cur = cand[1]; hold_end, hop_pt = cand[2]; path.append((cur, seg_start)); ok = hold_end >= en
        if not ok: continue
        segs.append((cur, seg_start, en))
        for q, a_, b_ in segs: bisect.insort(busy[q], (a_, b_))
        for (q1, _, h), (q2, _) in zip(segs[:-1], path[1:]):
            post[h] += [f"CX {q1} {q2}\n", f"CX {q2} {q1}\n"]; nhops += 1
        host_path[(P, k)] = (path[0][0], cur); on_extra += any(q in xs for q, _, _ in segs)
    repl = {}; nb = first_new_bit; saved = 0
    for P, lst in occ.items():
        for k, (L, a, b, t) in enumerate(lst):
            s_in = host_path.get((P, k - 1), (None, None))[1]; s_out = host_path.get((P, k), (None, None))[0]
            if s_in is None and s_out is None: continue
            out = []
            if s_in is not None: out.append(f"CX {s_in} {t}\n"); saved += 1
            else: out += [f"CCX {a} {b} {s_out}\n", f"CX {s_out} {t}\n"]
            if s_in is not None and s_out is not None: out.append(f"CX {s_in} {s_out}\n")
            if s_in is not None:
                out += [f"HMR {s_in} b{nb}\n", f"CZ {a} {b} if b{nb}\n"]; nb += 1
            repl[L] = out
    stats = dict(duplicate_pairs=sum(len(l) - 1 for l in occ.values() if len(l) > 1), pairs_considered=len(pairs), hosted=len(host_path), hops=nhops,
                 on_extra=on_extra, extra_qubits=len(xs), toffolis_saved=saved, new_bits=nb - first_new_bit)
    return repl, post, stats

def rewrite(src, dst, repl, post):
    with open(src) as f, open(dst, 'w') as g:
        for i, line in enumerate(f):
            if i in repl: g.writelines(repl[i])
            else: g.write(line)
            if i in post: g.writelines(post[i])