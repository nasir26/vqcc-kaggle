"""Per-phase Toffoli profile of a dqi circuit in kmx text form (uses the INFO_TAG @enter/@exit marks).

Counts CCX/CCZ/CSWAP per top-level mark and per (top, second-level) mark, split into unconditioned and
conditioned (inside PUSH_CONDITION or with an 'if bN' suffix). Also tracks a liveness proxy: a qubit is dead after
R/HMR (dead-init) and becomes live at its next use; reports the peak live count per top-level phase.

usage: python tasks/dqi/phase_profile.py circuit.kmx
"""
import collections
import re
import sys

TOF = {'CCX', 'CCZ', 'CSWAP'}
top = collections.Counter(); topc = collections.Counter(); sub = collections.Counter()
peak = collections.defaultdict(int); stack = []; cond = 0
live = set(); dead_ops = {'R', 'HMR'}
qre = re.compile(r'\bq(\d+)\b')
nq = 0
with open(sys.argv[1]) as f:
    for line in f:
        op, _, rest = line.rstrip("\n").partition(" ")
        if op == 'INFO_TAG':
            t = rest.strip().strip('"')
            if t.startswith('@enter:'):
                stack.append(t[7:])
            elif t.startswith('@exit:'):
                stack.pop()
            continue
        if op == 'PUSH_CONDITION':
            cond += 1; continue
        if op == 'POP_CONDITION':
            cond -= 1; continue
        if op in ('APPEND_TO_REGISTER', 'REGISTER'):
            continue
        key = stack[0] if stack else '(none)'
        if op in TOF:
            c = cond > 0 or ' if ' in rest
            (topc if c else top)[key] += 1
            sub[(key, stack[1] if len(stack) > 1 else '-', c)] += 1
        qs = qre.findall(rest)
        if op in dead_ops:
            for q in qs: live.discard(q)
        else:
            for q in qs: live.add(q)
        if len(live) > peak[key]: peak[key] = len(live)
tot = sum(top.values()) + sum(topc.values())
print(f'total toffoli-like {tot}  unconditioned {sum(top.values())}  conditioned {sum(topc.values())}')
for k in dict.fromkeys(list(top) + list(topc)):
    print(f'{k:20s} uncond {top[k]:8d}  cond {topc[k]:7d}  peak_live {peak[k]}')
print('--- second level')
for (a, b, c), v in sorted(sub.items(), key=lambda x: -x[1])[:60]:
    print(f'{a:16s} {b:34s} {"cond" if c else "    "} {v}')
