# "Silent Night" two-dog ornament: KiCad layer SVGs

The board itself is cut to the silhouette of the scene: a black Labrador and a yellow Labrador sit side by side and look up at a Christmas tree with a star on top. A ground strip along the bottom ties the three shapes into one board.

The board fits inside a 100 x 100 mm square (97 mm wide, 99 mm tall). Every SVG uses the origin at the top-left corner of that square, drawn at 1 SVG unit = 1 mm. Text has already been turned into outlines, and shapes with holes are split into hole-free pieces.

## How the colours are made
**Black solder mask + ENIG finish + white silkscreen.**
- **Yellow dog:** copper with the mask opened over it, so it comes out gold. The eye, ear, collar and the hatched shadow down its back are strips where the mask stays on the copper, so they read as black lines.
- **Black dog:** plain black mask. Its line work is white silkscreen, with a thin gold rim along the edges that face the star, and a gold eye and collar tag.
- **Tree:** black mask with white edge lines. The star and the hanging eyelet are gold.

## Board outline
- Inside corners have a radius of at least 1 mm, and nothing is narrower than 1.6 mm, so a standard 2 mm router bit can cut it. The narrowest parts are the stalk under the star (4 mm) and the trunk (5.2 mm).
- The gold stops 0.5 mm short of the board edge, which leaves a thin black outline around the yellow dog.
- There is a 3 mm hanging hole above the star. The board's centre of mass is about 27 mm to the left of that hole, so on a single hook it hangs tilted. It sits level standing on its flat base, or hung from a thread tied to the eyelet and looped under the black dog's chin.

## LEDs (from smt_tree.kicad_sch)
The circuit is an NE555 clocking a CD4017 decade counter at roughly 3.6 Hz. Each 4017 output drives one 0805 LED through 330 Ω, powered from USB-C.
- **D1 to D9** are the tree's baubles from bottom to top, and **D10** is in the centre of the star. Wired to Q0..Q9 in that order, the light climbs the tree and ends on the star.
- `_leds.txt` lists each LED's XY position in mm (rotation 0, top side). `05_User.Drawings_LED_guide.svg` draws their outlines.
- Each LED has a 4.8 x 2.2 mm clear area with no silkscreen and no art copper.
- Put the 555, 4017, resistors, caps and USB-C on **B.Cu**. The widest free areas on the back are behind the two dogs. The USB-C receptacle fits on the flat bottom edge of the ground strip. Tracks to the star LED have to run up the 4 mm stalk.

## Import (KiCad 8: PCB Editor > File > Import > Graphics…)
Use these settings for every file: Placement = At X 0, Y 0; Import scale = 1.0; tick "Group items".

| File | Import onto layer | What it does |
|---|---|---|
| 01_Edge.Cuts.svg | Edge.Cuts | The two-dogs-and-tree outline plus the hanging hole. |
| 02_F.Cu.svg | F.Cu | Copper under every gold area. It is unconnected, so keep your GND pour and tracks off the front around it. |
| 03_F.Mask.svg | F.Mask | Filled shapes are mask **openings**, which become the exposed ENIG gold. |
| 04_F.Silkscreen.svg | F.Silkscreen | Black dog line work, tree edges, ground line and "Silent Night". |
| 05_User.Drawings_LED_guide.svg | User.Drawings | Where the 10 LEDs go. |

There is no F.Paste art layer, because paste on the art would put solder on the gold. KiCad makes paste for the LED pads from the footprints.

## Fab notes
- Matte **black** mask, **white** silkscreen, **ENIG** finish (HASL would make the yellow dog silver), 1.6 mm FR4.

## Files
- `preview.png` shows the board unlit. `preview_lit.png` shows the moment the star LED (D10) is on.
- `source/build_ornament.py` regenerates every layer (Python 3 with shapely and fonttools). It needs the OFL font UnifrakturMaguntia saved as `source/fonts/frak.ttf`.
