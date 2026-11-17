# TIGRi thesis analysis code

This package reproduces the quantitative figures and supplementary tables in the final TIGRi thesis. It contains the six retained repression acquisitions and the five-acquisition time-course analysis, including the N-GS15 targeting versus non-targeting comparison.

## Manuscript outputs

| Output | Generated files | Source acquisitions |
|---|---|---|
| Figure 3B: baseline guide repression | `Figure-3B-guide-repression.pdf/png` | 12 May |
| Figure 4B–C: matched sites and NT controls | `Figure-4BC-matched-sites-and-controls.pdf/png` | 21 July; 1 August NEW |
| Figure 5: native and BoxB guide configurations | `Figure-5-boxb-repression.pdf/png` | 29 May |
| Figure 6: N- and C-terminal TadA8e fusions | `Figure-6-tada8e-fusions.pdf/png` | 8 and 11 June |
| Figure 7: repression time courses | `Figure-7-time-series.pdf/png` | 12 May; 8 and 11 June |
| Figures D1–D3: growth, fluorescence and normalized signals | `Figure-D1-time-series.pdf/png` through D3 | 29 May; 8 June; 21 July |
| Table D1: endpoint sensitivity | `Table-D1.csv` | Five time-course acquisitions |
| Table D2: N-GS15 control comparison | `Table-D2.csv`, `ngs15_summary.csv`, `ngs15_wells.csv` | 21 July |

Figures 1, 2, 3A and 4A are independently prepared schematics. They are not generated or bundled by this numerical pipeline. Figures 3B and 4B–C are exported as standalone quantitative panels for assembly with those schematics. Tables 1–4 and Appendices A–C describe methods or materials rather than calculated results.

## Run

Use Python 3.11 or later; the retained pipeline was validated with Python 3.12.14. Install the exact dependency versions in `requirements.txt`:

```powershell
python -m pip install -r requirements.txt
python run_analysis.py --data-root "D:/TIGRi-data" --output "D:/TIGRi-results"
```

`--data-root` must contain the `data/` tree with the six original Excel exports listed in `inputs/source_manifest.json`. `--output` must be a new or empty directory. Results are written there; source workbooks are read only. Run without `-O`, because integrity and numerical assertions are required.

The default fonts are Windows Arial and Arial Bold, matching the thesis. On another platform, supply readable font files explicitly:

```text
python run_analysis.py --data-root /path/to/data-root --output /path/to/results --font-regular /path/to/Arial.ttf --font-bold /path/to/Arial-Bold.ttf
```

Fonts are not redistributed. Different fonts can change figure layout; the numerical calculations are unchanged. Missing fonts stop the run rather than trigger a silent substitution.

## Package contents

| File | Responsibility |
|---|---|
| `run_analysis.py` | Validate source hashes and paths, then run the pipeline |
| `scripts/inputs.py` | Validate the versioned acquisition and well maps |
| `scripts/analyze_endpoints.py` | Read six source exports and calculate endpoint measurements and summary statistics |
| `scripts/analyze_timeseries.py` | Reconstruct five time courses and fixed-time/final-reading comparisons |
| `scripts/verify_timeseries.py` | Independently verify endpoint and time-course values against stored XLSX XML cells |
| `scripts/make_tables.py` | Format Tables D1–D2 and export the full-precision N-GS15 comparison |
| `scripts/plot_endpoints.py` | Draw endpoint bars, SDs, colony points and matched-site corrected repression |
| `scripts/plot_timeseries.py` | Draw Figure 7 and Figures D1–D3 |
| `scripts/config.py` | Resolve the runner's explicit paths and font settings |
| `inputs/source_manifest.json` | Required raw exports and SHA-256 hashes |
| `inputs/assay_map.json` | Retained sample-to-well assignments and endpoint reference values |
| `PROVENANCE.json` | Provenance of the retained analysis and plotting implementations |

The calculation produces full-precision well/group endpoint and time-course CSVs, acquisition metadata, fixed-time comparisons, an output manifest, and `verification.json`. Figures are vector PDFs plus PNGs rendered from the same drawing. These generated results need not be stored in the source repository.

## Inputs and compatibility

Both JSON inputs use `schema_version: 1`. The structured `assay_map.json` replaces the earlier HTML audit input; the HTML file and its unused acquisitions are not part of this package. Use the matching manifest and map from this version together. The six retained acquisition IDs are 0, 2, 3, 4, 9 and 11; they preserve the original audit identifiers, so they are deliberately not consecutive.

Each plate map contains group names, three N wells and three P wells, and reference endpoint values used to verify reconstruction. The pipeline rejects unsupported schemas, missing/changed raw exports, duplicate well assignments, incomplete reference maps, non-positive OD, partial reads and inconsistent endpoint values. It does not fill missing data or guess sample identities.

The 1 August map includes only the eight reported NT groups for dTasR and dSpyCas9. The acquisition labelled `old` is excluded because its well assignments could not be verified. The corrected 21 July N-GS15 NT assignment is guide pMC168 in G1–G6: N in G1–G3 and P in G4–G6.

## Calculation conventions

- Divide fluorescence by OD for each well, then calculate the mean and sample SD across the three colony-derived cultures in each condition.
- Report fold repression as the ratio of condition means, N/P. The underlying P/N ratio is retained for NT adjustment. Do not average three individual colony ratios.
- Corrected repression is `100 × [1 − (P/N)target / (P/N)NT]`, using the same acquisition, time and effector. N-GS15 uses its own NT condition, not the unfused dTasR NT condition.
- Table D2 displays an NT row as `Reference`. A negative targeting value means a smaller induction-associated decrease than its NT reference.
- Time courses pair OD and fluorescence by acquisition cycle, retaining the separate actual reading times. Endpoints use the nearest measured reading in each channel. There is no smoothing, interpolation or extrapolation.
- All three cultures are retained. There is no blank subtraction where a verified blank is unavailable, no pooling of independent dates, and no treatment of time points as independent replicates.
- The P/N cultures originate from splits of the colony-derived overnight cultures. The reported estimand remains the ratio of condition means; well order is not used to calculate a mean of paired ratios.

## Data and sharing

The raw Excel workbooks are supplied separately, subject to the supervisor's decision. They are not bundled here. The input map contains only the retained assignments and numerical endpoint reference checks, not the full raw time series or experimental notebook. Keep the original file paths from the source manifest beneath the chosen data root.

Plasmid sharing links belong to the thesis supplement and are separate from this analysis package. The package contains no manuscript, EndNote library, BioRender assets, raw workbooks, private review reports or document-editing scripts.

The source repository is https://github.com/JasdewStarfield/TIGRi-thesis-analysis. The `thesis-submission-2026-11-18` tag identifies the code version accompanying the submitted thesis.
