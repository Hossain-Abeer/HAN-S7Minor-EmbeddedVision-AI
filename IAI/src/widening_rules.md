# HSV Widening Rules & Justification

Raw bounds from `clothColor_noAspectRatio.png` were extracted via `clothColor_sampler.py`.
Raw data is saved in `clothColor_rawPixelValueSet.txt`.

## Raw Data vs. Polluted Data
The whole-cloth box included the white cue ball and wooden rails, producing polluted 
bounds (H: 0-174, S: 0-255). A targeted sample of the dark cloth shadow revealed 
the true cloth color: Hue ~90, Saturation > 160, Value > 39.

## Applied Rules
1. Hue (H): Fixed to 80-100. Captures teal. Rejects red/brown wood and other ball hues.
2. Saturation (S): Lower bound set to 100. Cloth is >160, cue ball is ~0. This cleanly 
   rejects the white cue ball and white stripes while keeping all cloth.
3. Value (V): Lower bound set to 30. Darkest cloth shadow was 39. Drops low enough 
   for pocket shadows but avoids pure black (V=0) which belongs to the 8-ball.