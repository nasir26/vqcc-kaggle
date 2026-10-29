"""Stage every distinct task member of downloaded public submissions as a single-task candidate.

For each data/public_out/<owner>__<notebook>/**/submission.zip: reject unsafe archives (absolute paths, '..',
links), group members by task (invsqrt.kmb|kmx, dqi.kmb|kmx, dfthcsos/), hash each task's bytes, and extract each
new (task, sha256) once into data/candidates/pub_<task>_<sha8>/ with a params.json naming every notebook that
ships it. Nothing is executed. Prints one line per (task, sha256).

Usage: python tools/scan_public.py [--root data/public_out] [--out data/candidates]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import stat
import zipfile

TASKS = ('invsqrt', 'dqi', 'dfthcsos')


def task_of(name: str) -> str | None:
    head = name.split('/', 1)[0]
    for t in TASKS:
        if head == t or head in (f'{t}.kmb', f'{t}.kmx'):
            return t
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=pathlib.Path, default=pathlib.Path('data/public_out'))
    ap.add_argument('--out', type=pathlib.Path, default=pathlib.Path('data/candidates'))
    a = ap.parse_args()
    seen: dict[tuple[str, str], dict] = {}
    for z in sorted(a.root.glob('*/**/submission.zip')):
        src = z.relative_to(a.root).parts[0]
        with zipfile.ZipFile(z) as zf:
            infos = [i for i in zf.infolist() if not i.is_dir()]
            for i in infos:
                n = i.filename
                if n.startswith('/') or '..' in pathlib.PurePosixPath(n).parts or stat.S_ISLNK(i.external_attr >> 16):
                    raise SystemExit(f'unsafe member {n!r} in {z}')
            groups: dict[str, list[zipfile.ZipInfo]] = {}
            for i in infos:
                t = task_of(i.filename)
                if t:
                    groups.setdefault(t, []).append(i)
            for t, members in groups.items():
                h = hashlib.sha256()
                for i in sorted(members, key=lambda i: i.filename):
                    h.update(i.filename.encode() + b'\0')
                    with zf.open(i) as f:
                        for chunk in iter(lambda: f.read(1 << 24), b''):
                            h.update(chunk)
                key = (t, h.hexdigest())
                if key in seen:
                    seen[key]['sources'].append(src)
                    continue
                d = a.out / f'pub_{t}_{key[1][:8]}'
                if not d.exists():
                    for i in members:
                        zf.extract(i, d)
                seen[key] = {'task': t, 'sha256': key[1], 'dir': str(d), 'sources': [src],
                             'bytes': sum(i.file_size for i in members)}
    for v in seen.values():
        (pathlib.Path(v['dir']) / 'params.json').write_text(json.dumps(
            {'note': 'public reproduction, unchanged bytes', 'sources': v['sources'], 'sha256': v['sha256']}, indent=1))
        print(json.dumps(v))


if __name__ == '__main__':
    main()
