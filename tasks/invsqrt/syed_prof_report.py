"""Aggregate syed_profile_build.py output (ours). Usage: syed_prof_report.py PROF.json [depth]"""
import json, sys
from collections import defaultdict, OrderedDict
from fractions import Fraction
d = json.load(open(sys.argv[1])); depth = int(sys.argv[2]) if len(sys.argv) > 2 else 3
cuts = d['cuts']
recs = d['records']
def stage_of(instr):
    prev = 'start'
    for c in cuts:
        if instr < c['instruction_cut']: return prev
        prev = c['name']
    return prev
agg = OrderedDict()
live = 0
for r in recs:
    if r['kind'] == 'alloc': continue
    st = stage_of(r['instr'])
    # drop frames up to and including the lifecycle body / build frames
    s = [f for f in r['stack'] if not f.startswith(('<frozen', 'runpy', 'syed_', 'build_variant'))]
    # keep frames after emit_body / build
    for anchor in ('emit_body', 'build'):
        idx = [i for i, f in enumerate(s) if f.endswith(':' + anchor)]
        if idx: s = s[idx[-1] + 1:]; break
    key = (st, ' > '.join(s[:depth]))
    a = agg.setdefault(key, dict(n=0, e=Fraction(0), peak=0, cond=0))
    a['n'] += 1; a['e'] += Fraction(r['p']); a['peak'] = max(a['peak'], r['live']); a['cond'] += r['cond'] > 0
tot = Fraction(0); cur = None; sub = Fraction(0)
for (st, f), a in agg.items():
    if st != cur:
        if cur is not None: print(f'   -- stage {cur}: {float(sub):.4f}')
        cur = st; sub = Fraction(0); print(f'== after cut "{st}"')
    sub += a['e']; tot += a['e']
    print(f"   {float(a['e']):9.4f} static {a['n']:4d} cond {a['cond']:4d} peak {a['peak']:2d}  {f}")
print(f'   -- stage {cur}: {float(sub):.4f}'); print('total', float(tot))
