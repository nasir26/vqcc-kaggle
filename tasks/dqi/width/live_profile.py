"""[ours] Structural live-qubit profile of a .kmx circuit.
A qubit is free from the start (unless it is an input register qubit) and after HMR or R; it becomes busy at the
next X / CX target / CCX target / SWAP touching it (a SWAP of two free qubits keeps both free).
Reports the peak, the number of instructions at peak, and per-qubit busy fractions.
usage: live_profile.py FILE.kmx NUM_INPUT_QUBITS [--dump-peaks N]"""
import sys, collections, json
path = sys.argv[1]; nin = int(sys.argv[2])
busy = {}  # qubit -> bool
for q in range(nin): busy[q] = True
live = nin; peak = live; at_peak = 0; line_no = 0
busy_lines = collections.Counter(); start = {}
CH = int(sys.argv[3]) if len(sys.argv) > 3 else 100000
chunkmax = collections.defaultdict(int)
hist = collections.Counter()
def mark(q):
    global live
    if not busy.get(q, False):
        busy[q] = True; live += 1; start[q] = line_no
def free(q):
    global live
    if busy.get(q, False):
        busy[q] = False; live -= 1; busy_lines[q] += line_no - start.get(q, 0)
with open(path) as f:
    for line in f:
        line_no += 1
        c = line[0]
        if c == 'A' or c == 'B' or c == 'P' or c == 'N': continue
        p = line.split()
        op = p[0]
        if op == 'CX': mark(int(p[2][1:]))
        elif op == 'CCX': mark(int(p[3][1:]))
        elif op == 'X': mark(int(p[1][1:]))
        elif op == 'SWAP':
            a, b = int(p[1][1:]), int(p[2][1:])
            if busy.get(a, False) != busy.get(b, False):
                ba = busy.get(a, False); busy[a] = busy.get(b, False); busy[b] = ba
                # transfer interval starts
                if busy[a]: start[a] = start.get(b, line_no)
                else: busy_lines[b] += 0
                if busy[b]: start[b] = start.get(a, line_no)
        elif op == 'HMR' or op == 'R': free(int(p[1][1:]))
        else: continue
        hist[live] += 1
        ch = line_no // CH
        if live > chunkmax[ch]: chunkmax[ch] = live
        if live > peak: peak = live; at_peak = 0
        if live == peak: at_peak += 1
for q, b in busy.items():
    if b: busy_lines[q] += line_no - start.get(q, 0)
print('lines', line_no, 'peak', peak, 'qubit-touching instrs at peak', at_peak)
print('histogram top:', sorted(hist.items())[-8:])
tl = [chunkmax[i] for i in range(max(chunkmax) + 1)]
print('timeline (max live per chunk of', CH, 'lines):')
print(' '.join(str(v - 800) for v in tl))
fr = sorted(((busy_lines[q] / line_no, q) for q in busy))
print('least busy qubits:', [(q, round(x, 4)) for x, q in fr[:12]])
json.dump(dict(peak=peak, timeline=tl, hist=sorted(hist.items())), open(path + '.live.json', 'w'))
