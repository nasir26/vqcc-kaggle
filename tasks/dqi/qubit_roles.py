"""Role timeline of chosen qubits in a kmx line range: for each op touching them print line, op, role.

usage: python tasks/dqi/qubit_roles.py circuit.kmx START END q1,q2,... [max_lines]
roles: T=target of CX/CCX, C=control, S=swap, M=HMR/R, X/Z, P=phase (CZ/CCZ)
"""
import re, sys
f, a, b, qs = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), set(sys.argv[4].split(','))
mx = int(sys.argv[5]) if len(sys.argv) > 5 else 10**9
out = 0
with open(f) as fh:
    for i, line in enumerate(fh, 1):
        if i < a: continue
        if i > b: break
        s = line.split()
        if not s: continue
        op = s[0]
        args = [x for x in s[1:] if x.startswith('q')]
        hit = [x for x in args if x in qs]
        if not hit and op != 'INFO_TAG': continue
        if op == 'INFO_TAG':
            continue
        print(i, line.rstrip()); out += 1
        if out >= mx: break
