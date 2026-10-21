"""Resolve packaged resource directories (templates, structs, store).

All paths are anchored to the package directory so that everything works
regardless of the current working directory (including when installed via
pip).
"""

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent

TEMPLATES_DIR = PACKAGE_DIR / "templates"
STRUCTS_DIR = PACKAGE_DIR / "structs"
STORE_DIR = PACKAGE_DIR / "store"
