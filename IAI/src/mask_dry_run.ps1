# src/mask_dry_run.ps1
# Quick test of mask extraction on 20 crops across classes.
# Mirrors src/extract_dry_run.ps1 from Section 3.

$env:EVML_DRY_RUN_CROPS = "20"

python src/mask.py

Remove-Item Env:EVML_DRY_RUN_CROPS