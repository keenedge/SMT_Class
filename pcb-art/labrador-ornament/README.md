# "Silent Night" Labrador ornament: KiCad layer SVGs

A noir/gothic Christmas ornament: a yellow Labrador sits in the snow and looks up at the star on top of a Christmas tree.

The board is a 90 mm disc with a gothic pointed cap, and fits inside a 100 x 100 mm square (90 mm wide, 100 mm tall).
Every SVG uses the same origin (the top-left corner of that 100 x 100 mm square) and is drawn at 1 SVG unit = 1 mm.
Text has already been turned into outlines, so no fonts are needed. Shapes with holes are split into hole-free pieces so KiCad imports them cleanly.

## How the yellow is made
**Black solder mask + ENIG finish.** The Labrador, the star, the baubles and the cap are copper with the mask opened over them, so they come out as bright gold (ENIG). Details such as the eye, ear, collar and fur hatching are thin strips where the mask stays on top of the copper, so they read as black lines inside the gold. The tree, moon, star rays, snow and frame are white silkscreen.

## Import (KiCad 8: PCB Editor > File > Import > Graphics…)
Use these settings for every file: Placement = At X 0, Y 0; Import scale = 1.0; tick "Group items".

| File | Import onto layer | What it does |
|---|---|---|
| 01_Edge.Cuts.svg | Edge.Cuts | Ornament outline plus a 3.5 mm hanging hole in the cap. |
| 02_F.Cu.svg | F.Cu | Copper under every gold area. It is 0.15 mm larger than the mask openings so the gold has crisp edges, and stays 0.5 mm from the board edge and hole. |
| 03_F.Mask.svg | F.Mask | Filled shapes are mask **openings**, which become the exposed ENIG gold. |
| 04_F.Silkscreen.svg | F.Silkscreen | White legend art. It is already pulled back 0.25 mm from the gold, and features are at least 0.15 mm. |

There is no F.Paste (stencil) layer on purpose. A paste stencil would put solder on the gold, turning it silver and lumpy. If you do add parts later, KiCad generates paste from the footprints anyway.

If you don't want the art copper connected to anything, leave it as plain graphics on F.Cu. KiCad treats it as unconnected copper. Don't add a copper pour.

## Fab notes
- Solder mask: **black** (matte black looks the most noir). Silkscreen: **white**.
- Surface finish: **ENIG**. HASL would make the dog silver.
- 1.6 mm FR4. No components are needed. It's a pure art board.

## Files
- `preview.png` is a rendering of the finished board.
- `source/build_ornament.py` regenerates every layer (Python 3 with shapely and fonttools). It needs the OFL font UnifrakturMaguntia saved as `source/fonts/frak.ttf`.
