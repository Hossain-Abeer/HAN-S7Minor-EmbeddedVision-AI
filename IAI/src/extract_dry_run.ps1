# src/extract_dry_run.ps1
# Quick test of the extraction pipeline on 100 frames of Clip 1

$env:EVML_DRY_RUN_CLIPS="1"
$env:EVML_DRY_RUN_FRAMES="10000"

python src/extract_crop.py

Remove-Item Env:EVML_DRY_RUN_CLIPS, Env:EVML_DRY_RUN_FRAMES