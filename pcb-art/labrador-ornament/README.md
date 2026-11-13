# "No More Silent Nights" dogs-and-tree ornament: KiCad layer SVGs

The board itself is cut to the silhouette of the scene: a black Labrador and a yellow Labrador look up at a Christmas tree with a star on top. A small white dog with an antler tied to its head sits in front of them, and a wrapped present with a big bow sits bottom right, with its lid pushed askew by a puppy peeking out from under it, and the puppy's tail poking out the other side. A ground strip ties everything into one board.

The board fits inside an **85 x 85 mm** square (84.0 mm wide, 85.0 mm tall). Every SVG uses the origin at the top-left corner of that square, drawn at 1 SVG unit = 1 mm. Text has already been turned into outlines, and shapes with holes are split into hole-free pieces.

## How the colours are made
**Black solder mask + ENIG finish + white silkscreen.**
- **Yellow dog:** copper with the mask opened over it, so it comes out gold. Its details are strips of mask left on the copper.
- **Black dog:** plain black mask with white silkscreen line work, a thin gold rim on the edges facing the star, and a gold eye and tag.
- **Guide dog jackets:** both Labs wear a training jacket lettered "BCAGD" (BC & Alberta Guide Dogs), with the letters following the curve of the dog's back. The black dog's jacket is solid white silkscreen with the letters left black. The yellow dog's jacket is black mask with a white outline and white letters. The letters are about 2.6 mm tall on the black dog and 2.2 mm on the yellow dog. To change the word, set `JK_WORD` when running the build script.
- **White dog:** solid white silkscreen with black details and a gold bell.
- **Present:** gold ribbon and bow, white box outline. The puppy's head, paws and tail are gold with dark engraved details.
- **Tree:** black mask with white edge lines. The dogs and the present sit in front of it. The star, the hanging eyelet and the present's ribbon are gold.

## Balance
The 3 mm hanging hole is above the star at X = 52.84 mm. The CR2032 holder goes on the back behind the present, centred at X = 70.26, Y = 73.32, and acts as the counterweight.

| Item | Mass used | Centre X |
|---|---|---|
| Bare board (1.6 mm FR4, 33 cm²) | 10.0 g | 45.0 mm |
| CR2032 cell + SMD holder | 4.5 g (3.0 g + 1.5 g) | 70.3 mm |
| **Combined** | 14.5 g | **52.84 mm** |

With those numbers the centre of mass is 0.01 mm from the hang line, so it hangs straight. Without the battery it tilts about 9°.

These are estimates. Weigh your actual holder: every 1 g of difference in the battery assembly moves the balance point about 1.25 mm (about 1.2°). To trim, slide the holder: moving it 1 mm sideways moves the balance point about 0.3 mm. The ICs and passives weigh under 1 g in total. Placing them near X = 53 on the back keeps them out of the balance.

## Outline notes
- Inside corners have a radius of at least 1 mm, and nothing is narrower than 1.6 mm. The narrowest part is the stalk under the star (4.5 mm).
- Gold stops 0.5 mm short of the board edge.

## LEDs and power (from smt_tree.kicad_sch)
The circuit is an NE555 clocking a CD4017 at roughly 3.6 Hz, one 0805 LED per output through 330 Ω.
- The ten LEDs are spread over the scene. `_leds.txt` has every XY position and rotation, plus the battery holder centre.

| LED | Where | Rotation |
|---|---|---|
| D1 to D4 | Tree baubles, bottom to top | 0° |
| D5 | Centre of the star | 0° |
| D6 | Black Lab's eye | 0° |
| D7 | Yellow Lab's eye | 0° |
| D8 | White dog's chest, like a glowing bell | 90° |
| D9, D10 | The puppy's two eyes | 90° |

- The 4017 lights one LED at a time. Wired to Q0..Q9 in this order, the light climbs the tree to the star, visits each dog, then the puppy winks one eye after the other. To make both puppy eyes light together you would have to drive D9 and D10 from one output, which frees one output.
- Tree and star LEDs have a 4.4 x 2.0 mm clear area. The LEDs on the dogs have a tighter 3.7 x 1.8 mm clear area so the faces survive, which means their vias need to sit close to the pads or in them.
- The puppy's eyes are only 3.4 mm apart, so D9 and D10 stand upright side by side. 0805 parts fit, but they cover most of the puppy's face. 0603 LEDs on those two positions would look better.
- **Running from a CR2032 (3 V) needs changes to the schematic.** A standard NE555 needs at least 4.5 V, so swap it for a CMOS 555 such as TLC555 or LMC555 (same SOIC-8 footprint). Blue and white LEDs will be dim or dark at 3 V through 330 Ω, so use red, amber or yellow-green, or lower the resistors. The USB-C connector and its 5k1 resistors are no longer needed.
- Use a surface-mount holder on B.Cu, so no pins come through the present on the front. The present is 24.5 x 24.5 mm, so pick a compact holder and check its footprint fits. Its pads can extend left onto the ground strip.

## Import (KiCad 8: PCB Editor > File > Import > Graphics…)
Use these settings for every file: Placement = At X 0, Y 0; Import scale = 1.0; tick "Group items".

| File | Import onto layer | What it does |
|---|---|---|
| 01_Edge.Cuts.svg | Edge.Cuts | The board silhouette plus the hanging hole. |
| 02_F.Cu.svg | F.Cu | Copper under every gold area. It is unconnected, so keep pours and tracks off the front around it. |
| 03_F.Mask.svg | F.Mask | Filled shapes are mask **openings**, which become the exposed ENIG gold. |
| 04_F.Silkscreen.svg | F.Silkscreen | White dog, black dog line work, tree edges, present outline, ground line and "No More Silent Nights". |
| 05_User.Drawings_LED_guide.svg | User.Drawings | The 10 LED positions and the 20 mm coin cell circle. |

There is no F.Paste art layer, because paste on the art would put solder on the gold.

## Fab notes
- Matte **black** mask, **white** silkscreen, **ENIG** finish, 1.6 mm FR4. A different board thickness changes the balance.

## Files
- `preview.png` shows the board unlit. `preview_lit.png` shows the star LED (D5) on. `preview_all_lit.png` shows all ten positions lit at once, which the real circuit never does.
- `source/build_ornament.py` regenerates every layer and prints the balance (Python 3 with shapely and fonttools). It needs the OFL font UnifrakturMaguntia saved as `source/fonts/frak.ttf`.
