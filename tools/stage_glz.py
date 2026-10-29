"""Stage chemistry sets from the public dataset dmitriigluzdov/vqcc-femoco-public-factorization (Apache-2.0).

Each data/candidates/glz_<name>/ gets dfthcsos/ (angle_k_*.kmb + submission.npz) from one open_circuits_* folder,
optionally with the weights (submission.npz) of another folder: v34 holds refitted weights for the v33 circuits.
Copies are real files (the metric rejects hardlinks).

usage: python tools/stage_glz.py [--files DIR] [--out data/candidates]
"""
import argparse
import json
import pathlib
import shutil

SETS = [(v, v, None) for v in ['open_circuits'] + [f'open_circuits_v{i}' for i in range(21, 30)]]
SETS += [('open_circuits_v29_w30', 'open_circuits_v29', 'open_circuits_v30'),
         ('open_circuits_v33_w34', 'open_circuits_v33', 'open_circuits_v34')]


def stage(files, out, name, circ_dir, npz_dir):
    d = out / f'glz_{name}'
    if d.exists():
        shutil.rmtree(d)
    (d / 'dfthcsos').mkdir(parents=True)
    src = files / circ_dir
    for p in src.iterdir():
        if p.name.startswith('dfthcsos__angle_k_'):
            shutil.copy(p, d / 'dfthcsos' / p.name.replace('dfthcsos__', ''))
    if (src / 'dfthcsos').is_dir():
        for p in (src / 'dfthcsos').iterdir():
            shutil.copy(p, d / 'dfthcsos' / p.name)
    w = files / (npz_dir or circ_dir)
    npz = w / 'dfthcsos__submission.npz'
    if not npz.exists():
        npz = w / 'dfthcsos' / 'submission.npz'
    if npz.exists():
        shutil.copy(npz, d / 'dfthcsos' / 'submission.npz')
    (d / 'params.json').write_text(json.dumps({
        'note': 'public reproduction (dmitriigluzdov/vqcc-femoco-public-factorization, Apache-2.0)',
        'circuits': circ_dir, 'weights': npz_dir or circ_dir}))
    print(name, len(list((d / 'dfthcsos').iterdir())), 'files')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--files', type=pathlib.Path,
                    default=pathlib.Path('data/public_out/dmitriigluzdov__vqcc-femoco-public-factorization/files'))
    ap.add_argument('--out', type=pathlib.Path, default=pathlib.Path('data/candidates'))
    a = ap.parse_args()
    for name, circ, npz in SETS:
        if (a.files / circ).is_dir():
            stage(a.files, a.out, name, circ, npz)


if __name__ == '__main__':
    main()
