# IPO Scope Lock (0.4)

## In scope
- Input: 5× 1080p .mp4 from DATA_ROOT/game1/
- Classes: CUE, SOLID, STRIPE
- 8-ball classification: SOLID
- UNCERTAIN: first-class label, yellow "?", separate counter
- Output: overlay + console log + optional VideoWriter

## Out of scope
- OCR / numeral reading (owned by IAI)
- Camera / webcam capture
- Per-ball crop cache (real-time pipeline only)
- Temporal voting
- Surface-colour feature
- Deep learning / ML

## Rubric coverage
| Criterion | Covered by |
|---|---|
| Acquisition | VideoCapture on .mp4 |
| Enhancement | GaussianBlur + HSV ordering |
| Segmentation  | inRange cloth mask + invert + morph + contours |
| Features (≥2) | white_ratio + edge_density |
| Classification | rule-based if/else |
| Complexity   | glare / overlap / lighting mitigations |
| Explanation  | design_rationale.md + parameters.md |