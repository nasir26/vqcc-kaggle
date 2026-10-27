"""Print kickmix's public API (names + docstrings) so we use only what exists.

Usage (WSL): python tools/kickmix_api.py DATA_DIR [NAME ...]
With NAMEs (e.g. CircuitBuilder.mark), prints full help for those attributes.
"""
import inspect
import sys

sys.path.append(f'{sys.argv[1]}/kickmix')
import kickmix as km  # noqa: E402

names = sys.argv[2:]
if names:
    for name in names:
        obj = km
        for part in name.split('.'):
            obj = getattr(obj, part)
        print(f'=== {name}')
        print(inspect.getdoc(obj) or '(no doc)')
        print()
else:
    for name in sorted(dir(km)):
        if name.startswith('_'):
            continue
        obj = getattr(km, name)
        first = (inspect.getdoc(obj) or '').split('\n')[0]
        print(f'{name}: {first}')
        if inspect.isclass(obj):
            for attr in sorted(a for a in dir(obj) if not a.startswith('_')):
                doc = (inspect.getdoc(getattr(obj, attr)) or '').split('\n')[0]
                print(f'    .{attr}: {doc}')
