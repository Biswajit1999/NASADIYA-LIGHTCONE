from __future__ import annotations

import json
from pathlib import Path


def test_publication_evidence_notebook_is_valid_json_notebook() -> None:
    path = Path(__file__).resolve().parents[1] / "notebooks" / "DESI_DR1_Publication_Evidence_Colab.ipynb"
    notebook = json.loads(path.read_text(encoding="utf-8"))
    assert notebook["nbformat"] == 4
    assert notebook["metadata"]["colab"]["name"] == "DESI_DR1_Publication_Evidence_Colab.ipynb"
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook["cells"])
    assert "build_desi_publication_figures.py" in source
    assert "DATA_PATH" in source
    assert "publication_evidence.zip" in source
