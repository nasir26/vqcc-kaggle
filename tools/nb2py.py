"""Print the cells of a .ipynb as plain text (for reading notebooks without Jupyter)."""
import json
import sys

nb = json.load(open(sys.argv[1], encoding="utf-8"))
for i, cell in enumerate(nb["cells"]):
    print(f"## cell {i} [{cell['cell_type']}]")
    print("".join(cell["source"]))
    print()
