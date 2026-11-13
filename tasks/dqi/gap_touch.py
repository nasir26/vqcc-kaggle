"""For consecutive peak runs, record which wires are touched in each gap (between run k's end and run k+1's start).
usage: python tasks/dqi/gap_touch.py circuit.kmx runs.json out.json
"""
import sys, json
runs = json.load(open(sys.argv[2]))
gaps = [(runs[k]['end'], runs[k + 1]['start']) for k in range(len(runs) - 1)]
sets = [set() for _ in gaps]
k = 0
with open(sys.argv[1]) as f:
    for ln, line in enumerate(f, 1):
        while k < len(gaps) and ln >= gaps[k][1]: k += 1
        if k >= len(gaps): break
        if gaps[k][0] < ln < gaps[k][1]:
            for x in line.split()[1:]:
                if x[0] == 'q': sets[k].add(int(x[1:]))
json.dump([sorted(s) for s in sets], open(sys.argv[3], 'w'))
print('gaps', len(gaps))
