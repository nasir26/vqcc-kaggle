"""Write the `SOURCES = {path: text}` dict embedded in a public notebook (code.py from tools/nb2py.py) to DIR/src/.

Text is only parsed with ast.literal_eval and written out; nothing is executed. Paths with '..' or a leading '/'
are refused.

usage: python -I tools/extract_sources.py NOTEBOOK_DIR
"""
import ast
import pathlib
import sys

d = pathlib.Path(sys.argv[1])
for line in (d / 'code.py').read_text(encoding='utf-8').split('\n'):
    if line.startswith('SOURCES = '):
        sources = ast.literal_eval(line[len('SOURCES = '):])
        break
else:
    sys.exit(f'no SOURCES dict in {d}/code.py')
for k, v in sources.items():
    assert '..' not in pathlib.PurePosixPath(k).parts and not k.startswith('/'), k
    p = d / 'src' / k
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(v, encoding='utf-8')
print(f'{len(sources)} files -> {d}/src')
