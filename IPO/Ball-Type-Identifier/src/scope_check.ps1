$src = "src"
$forbidden = @(
  "webcam", "VideoCapture\(0\)", "OCR", "tesseract",
  "digit", "numeral", "class 4", "BallType::EIGHT",
  "TemporalVote", "temporal_vote"
)
$hits = 0
foreach ($p in $forbidden) {
  $m = Get-ChildItem $src -Recurse -File -Include *.cpp,*.h,*.hpp |
       Select-String -Pattern $p
  if ($m) { $m | ForEach-Object { Write-Host "HIT: $_" }; $hits++ }
}
if ($hits -eq 0) { Write-Host "SCOPE OK" } else { Write-Host "SCOPE VIOLATION: $hits" }