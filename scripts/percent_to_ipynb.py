from __future__ import annotations

import json
import sys
from pathlib import Path


def markdown_source(lines: list[str]) -> list[str]:
    output = []
    for line in lines:
        if line.startswith("# "):
            output.append(line[2:])
        elif line.startswith("#"):
            output.append(line[1:])
        else:
            output.append(line)
    return [line + "\n" for line in output]


def convert(source_path: Path, output_path: Path) -> None:
    lines = source_path.read_text(encoding="utf-8").splitlines()
    cells = []
    current_type = None
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_lines
        if current_type is None:
            return
        if current_type == "markdown":
            cells.append(
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": markdown_source(current_lines),
                }
            )
        else:
            cells.append(
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": [line + "\n" for line in current_lines],
                }
            )
        current_lines = []

    for line in lines:
        if line == "# %% [markdown]":
            flush()
            current_type = "markdown"
        elif line == "# %%":
            flush()
            current_type = "code"
        else:
            current_lines.append(line)
    flush()

    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    output_path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: percent_to_ipynb.py SOURCE.py OUTPUT.ipynb")
    convert(Path(sys.argv[1]), Path(sys.argv[2]))
