# "Silent Night" Labrador ornament (noir): KiCad layer SVGs

A noir Christmas ornament. The star on top of the tree is the only light in the scene. Hard-edged shafts of light fall from it onto a yellow Labrador, whose face and chest are lit in gold while its back drops into black silhouette, and the dog throws a long shadow across a pool of lit snow. The tree is a black silhouette edged in white. Its baubles are the 10 LEDs from the `smt_tree` circuit.

The board is a 90 mm disc with a gothic cap, and fits inside a 100 x 100 mm square. There is a 3.5 mm hanging hole, and a 14 mm flat at the bottom edge for the USB-C power connector.
Every SVG uses the origin at the top-left corner of that 100 x 100 mm square, drawn at 1 SVG unit = 1 mm. Text has already been turned into outlines, and shapes with holes are split into hole-free pieces.

## How the yellow is made
**Black solder mask + ENIG finish.** The gold areas (the dog's lit side, the star, the bauble caps and the eyelet) are copper with the mask opened over them. The dog's eye, ear, mouth and collar are thin strips where the mask stays on top of the copper, so they read as black lines in the gold. Everything white is silkscreen.

## LEDs (from smt_tree.kicad_sch)
The circuit is an NE555 clocking a CD4017 decade counter at roughly 3.6 Hz (R1 10k, R2 2M, C 100n). Each 4017 output drives one 0805 LED through 330 Ω, and the board is powered from USB-C (5k1 on CC).
- **D1 to D9** sit on the tree as baubles, from bottom to top. **D10** sits in the centre of the star.
- With the LEDs placed in D1..D10 order on Q0..Q9, the light climbs the tree one LED at a time and finishes on the star. Then it repeats.
- `_leds.txt` lists the XY position of each LED in mm (rotation 0, top side). `05_User.Drawings_LED_guide.svg` draws their outlines.
- Each LED has a 4.8 x 2.2 mm clear area with no silkscreen and no art copper. That leaves room for the pads plus a via at each end to drop to the back.
- Put the 555, 4017, resistors, caps and USB-C on **B.Cu**. The back has no art, so it is all yours. The USB-C receptacle goes on the bottom flat.

## Import (KiCad 8: PCB Editor > File > Import > Graphics…)
Use these settings for every file: Placement = At X 0, Y 0; Import scale = 1.0; tick "Group items".

| File | Import onto layer | What it does |
|---|---|---|
| 01_Edge.Cuts.svg | Edge.Cuts | Ornament outline, the USB-C flat, and the hanging hole. |
| 02_F.Cu.svg | F.Cu | Copper under every gold area. It is 0.15 mm larger than the mask openings and stays 0.5 mm from the edge. This copper is unconnected, so keep your GND pour and tracks off the front around it. |
| 03_F.Mask.svg | F.Mask | Filled shapes are mask **openings**, which become the exposed ENIG gold. |
| 04_F.Silkscreen.svg | F.Silkscreen | Light beams, lit snow, tree outline, frame and "Silent Night". It is pulled back 0.25 mm from the gold and clear of the LEDs. |
| 05_User.Drawings_LED_guide.svg | User.Drawings | Where the 10 LEDs go. |

There is no F.Paste art layer, because paste on the art would put solder on the gold. KiCad makes paste for the LED pads from the footprints.

## Fab notes
- Matte **black** mask, **white** silkscreen, **ENIG** finish (HASL would make the dog silver), 1.6 mm FR4.

## Files
- `preview.png` shows the board unlit. `preview_lit.png` shows the moment the star LED (D10) is on.
- `source/build_ornament.py` regenerates every layer (Python 3 with shapely and fonttools). It needs the OFL font UnifrakturMaguntia saved as `source/fonts/frak.ttf`.
