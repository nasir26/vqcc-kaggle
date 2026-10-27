"""Dump every Kaggle competition page (rules, evaluation, ...) to data/pages/<name>.md."""
import pathlib
import sys

from kaggle.api.kaggle_api_extended import KaggleApi

SLUG = "google-verifiable-quantum-circuit-compilation"


def main(out_dir: str) -> None:
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    api = KaggleApi()
    api.authenticate()
    for page in api.competition_list_pages(SLUG):
        path = out / (page.name.replace(" ", "_") + ".md")
        path.write_text(page.content or "", encoding="utf-8")
        print(f"{page.name}: {len(page.content or '')} chars -> {path}")


if __name__ == "__main__":
    main(sys.argv[1])
