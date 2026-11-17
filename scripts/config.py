"""Shared explicit paths; importing an analysis never locates personal files."""
from pathlib import Path
import os

PACKAGE=Path(__file__).resolve().parents[1]
# The runner supplies these values. Missing configuration stops the calculation
# rather than silently using a different data folder or overwriting prior work.
ROOT=Path(os.environ['TIGR_DATA_ROOT']).resolve()
OUT=Path(os.environ['TIGR_OUTPUT']).resolve()
AUDIT=PACKAGE/'inputs/assay_map.json'
FONT_REGULAR=Path(os.environ.get('TIGR_FONT_REGULAR','C:/Windows/Fonts/arial.ttf'))
FONT_BOLD=Path(os.environ.get('TIGR_FONT_BOLD','C:/Windows/Fonts/arialbd.ttf'))
OUT.mkdir(parents=True,exist_ok=True)
