# "No More Silent Nights" dogs-and-tree ornament: KiCad layer SVGs

The board itself is cut to the silhouette of the scene: a black Labrador and a yellow Labrador look up at a Christmas tree with a star on top. A small white dog with an antler tied to its head sits in front of them, and a wrapped present with a big bow sits bottom right, with its lid pushed askew by a puppy peeking out from under it, and the puppy's tail poking out the other side. A ground strip ties everything into one board.

The board fits inside an **85 x 85 mm** square (83.7 mm wide, 84.8 mm tall). Every SVG uses the origin at the top-left corner of that square, drawn at 1 SVG unit = 1 mm. Text has already been turned into outlines, and shapes with holes are split into hole-free pieces.

## How the colours are made
**Black solder mask + ENIG finish + white silkscreen.**
- **Yellow dog:** copper with the mask opened over it, so it comes out gold. Its details are strips of mask left on the copper.
- **Black dog:** plain black mask with white silkscreen line work, a thin gold rim on the edges facing the star, and a gold eye and tag.
- **Guide dog jackets:** both Labs wear a training jacket lettered "BCAGD" (spelling to be confirmed) (BC & Alberta Guide Dogs), with the letters following the curve of the dog's back. The black dog's jacket is solid white silkscreen with the letters left black. The yellow dog's jacket is black mask with a white outline and white letters. The letters are about 2.6 mm tall on the black dog and 2.2 mm on the yellow dog. To change the word, set `JK_WORD` when running the build script.
- **White dog:** solid white silkscreen with black details and a gold bell.
- **Present:** gold ribbon and bow, white box outline. The puppy's head, paws and tail are gold with dark engraved details.
- **Tree:** black mask with white edge lines. The dogs and the present sit in front of it. The star, the hanging eyelet and the present's ribbon are gold.

## Balance
The 3 mm hanging hole is above the star at X = 47.83 mm. There is no battery: the board is powered over USB-C, and the USB-C receptacle (about 1 g) plus the ICs and passives, all in the gift box, act as a small counterweight.

| Item | Mass used | Centre X |
|---|---|---|
| Bare board (1.6 mm FR4, 33 cm²) | 9.8 g | 44.3 mm |
| USB-C receptacle + ICs + passives (front of the gift box) | 1.5 g (estimate) | 71.2 mm |
| **Combined** | 11.3 g | **47.84 mm** |

With those numbers the centre of mass is 0.01 mm from the hang line, so it hangs straight. To get there the tree and hang point moved left by about 5 mm compared to the coin cell version, because there is no heavy battery on the right any more.

These are estimates. Weigh the real parts: every 0.5 g of difference in the parts group moves the balance point about 0.5 mm, about 0.5°. The connector sits at the bottom edge, so a hanging USB cable will pull the ornament slightly. Unplug it when displaying, or run the cable straight down from the connector.

## Outline notes
- Inside corners have a radius of at least 1 mm, and nothing is narrower than 1.6 mm. The narrowest part is the stalk under the star (4.5 mm).
- Gold stops 0.5 mm short of the board edge.

## LEDs and power (from smt_tree.kicad_sch)
The circuit is a TLC555 (CMOS 555) clocking a 74HC4017 at roughly 3.6 Hz, powered from 5 V USB. There are 10 LEDs: 7 on the tree in 5 groups, 1 in the star, 2 in the puppy's eyes, and none on the dogs. `_leds.txt` has every XY position and rotation, plus the USB-C connector position. The schematic file has **not** been edited yet.

| LED | Where | Group | Rotation |
|---|---|---|---|
| D1, D2 | Tree, lowest tier | 1 | 0° |
| D3, D4 | Tree, second tier | 2 | 0° |
| D5 | Tree, middle | 3 | 0° |
| D6 | Tree, upper | 4 | 0° |
| D7 | Tree, just under the star | 5 | 0° |
| D8 | Centre of the star | star | 0° |
| D9, D10 | Puppy's left and right eye | eyes | 90° |

**The 10 stages** (one 4017 output per stage, Q0 to Q9):

| Stage | Lit | 4017 output |
|---|---|---|
| 1 | Tree group 1 (D1, D2) | Q0 |
| 2 | Tree group 2 (D3, D4) | Q1 |
| 3 | Tree group 3 (D5) | Q2 |
| 4 | Tree group 4 (D6) | Q3 |
| 5 | Tree group 5 (D7) | Q4 |
| 6 | Star only (D8) | Q5 |
| 7 | Star only (D8) | Q6 |
| 8 | Puppy, both eyes (D9, D10) | Q7 |
| 9 | All off | Q8 (nothing connected) |
| 10 | Puppy, both eyes (D9, D10) | Q9 |

`stage_01.png` to `stage_10.png` show each stage and `preview_stages.png` is a contact sheet of all ten.

**Wiring plan**
- Tree: each group's output drives its LEDs, one 1 kΩ resistor per LED, about 2 mA each. Groups 1 and 2 have two LEDs, so they load an output with about 4 mA, which is what a 74HC4017 can drive. A CD4017B can only source about 1 mA at 5 V, so use the 74HC4017 (same pinout).
- Star: D8 is fed from Q5 and Q6 through two small signal diodes (diode-OR) and one resistor.
- Puppy eyes: D9 and D10 are fed from Q7 and Q9 through two small diodes into a shared node, then one resistor per eye.
- Q8 is left unconnected, which gives the all-off stage.
- Assumption: each tree group lights alone, one after another, so the light climbs the tree. If you want the tree to build up (earlier groups stay on), the groups would need diode-OR from the later outputs instead.
- Tree and star LEDs have a 4.4 x 2.0 mm clear area; the puppy eyes have a tighter 3.5 x 2.0 mm area, so their vias should sit close to the pads or in them.
- The puppy's eyes are only 3.4 mm apart, so D9 and D10 stand upright side by side. 0805 parts fit but cover most of the face; 0603 would look better.
- **Power is USB-C only, 5 V, no cell.** U1 must be a CMOS 555 (TLC555) because a bipolar NE555 at 5 V gives only about 3.5 V logic high, which is marginal for the 4017 clock input. White and blue LEDs work at 5 V. J1 needs two 5.1 kΩ CC resistors (R13, R14). Add ESD or reverse protection if you like.
- **Parts layout.** Everything is SMT on the front, inside the gift box with the LEDs. There are no through-hole parts and nothing on the back. The short gold ribbon stub under the lid is all that is left of the vertical ribbon.
  - Layout in the gift box: U2 (74HC4017, SOIC-16) at left, U1 (TLC555, SOIC-8) next to it, 10 0805 parts (R1, R2, R13, R14, C1, C2 and the diodes D11 to D14) in two blocks right of the ICs, and J1 (USB-C) at the bottom edge. The ten LED series resistors R3 to R12 sit right next to their LEDs: R3 to R10 on the tree and star (2.4 to 3.5 mm from the LED), R11 and R12 just below the puppy's paws. `smt_tree.kicad_pcb` has them placed, and `preview_pcb_layout.png` shows the pads. `_leds.txt` and `parts.json` have the coordinates.
  - The USB-C footprint is the GCT USB4135-GF-A 6-pin top-mount from the original project, rotated so its mouth points down and overhangs the bottom edge by about 0.5 mm. Change it if you pick another receptacle.
  - The parts sit on black mask. Pads stay at least 0.25 mm from gold art copper (checked), and reference designators are on F.Fab so the silkscreen art stays clean.

## KiCad project files
The repository root has the updated `smt_tree.kicad_sch` and `smt_tree.kicad_pcb`. The PCB is built from the same layers as the SVGs: the board outline, hanging hole, F.Cu art, F.Mask openings and F.Silkscreen art are drawn as graphic polygons, with the board's top-left corner at X = 100, Y = 60 on the KiCad sheet. All 33 footprints are placed and carry their nets. **Nothing is routed yet**: open it, press **Update PCB from Schematic** (F8) if prompted, and route the ratsnest. The files were generated without KiCad here, so run ERC and DRC first and tell me about any errors.

## Import (KiCad 8: PCB Editor > File > Import > Graphics…)
Only needed if you want the art in another project. Skip this if you use `smt_tree.kicad_pcb`.
Use these settings for every file: Placement = At X 0, Y 0; Import scale = 1.0; tick "Group items".

| File | Import onto layer | What it does |
|---|---|---|
| 01_Edge.Cuts.svg | Edge.Cuts | The board silhouette plus the hanging hole. |
| 02_F.Cu.svg | F.Cu | Copper under every gold area. It is unconnected, so keep pours and tracks off the front around it. |
| 03_F.Mask.svg | F.Mask | Filled shapes are mask **openings**, which become the exposed ENIG gold. |
| 04_F.Silkscreen.svg | F.Silkscreen | White dog, black dog line work, tree edges, present outline, ground line and "No More Silent Nights". |
| 05_User.Drawings_LED_guide.svg | User.Drawings | The 10 LED positions, the front parts zones in the gift box and the USB-C connector position. |

There is no F.Paste art layer, because paste on the art would put solder on the gold.

## JLCPCB manufacturability review
Checked against JLCPCB's published capabilities (rigid PCB page, board outline guide, assembly pages) on the final 85 mm geometry. The check script is at the end of `source/build_ornament.py`.

| Rule (JLCPCB) | This board | Result |
|---|---|---|
| Copper to routed edge >= 0.2 mm | 0.37 mm | Pass |
| Copper to the hanging hole >= 0.5 mm (advised) | 0.55 mm | Pass (was 0.37 before this review, so the gold eyelet ring was moved out) |
| Routed internal corner radius >= 0.5 to 1.0 mm | Notches narrower than 2.0 mm are closed up, so every inside corner is >= 1 mm radius | Pass |
| Routed slot / notch width >= 1.0 mm | Narrowest notch is about 2.0 mm | Pass |
| Single closed outline | One outline plus the circular hanging hole, 1236 vertices, shortest segment 0.06 mm | Pass |
| Non-plated hole >= 0.5 mm | 3.0 mm hanging hole | Pass |
| Black mask bridge >= 0.13 mm | Only 0.003 mm² specks are below this, at tapered engraving ends | Pass (cosmetic) |
| Copper spacing >= 0.10 mm | Gaps below 0.16 mm are filled in, so none remain | Pass |
| Silkscreen line >= 0.15 mm, text >= 1.0 mm tall | Smallest letters are 2.6 mm tall (jackets), caption is 3.3 mm. A few small slivers (about 1.3 mm² in total) remain at tapered line ends | Pass (cosmetic) |
| Silkscreen to mask opening >= 0.15 mm | 0.21 mm | Pass |
| LED pads to art copper | 0.25 mm minimum, with mask dams to match | Pass (the first version had 0.06 mm here, which would fail) |
| Board size for assembly >= 70 x 70 mm | 83.7 x 84.8 mm | Pass |

**Things to know before ordering:**
- **Delicate tips.** The tree's branch tips and the star's points are narrower than 2 mm at the very end, as thin as 1.6 mm. They cut fine but can chip in handling. The unsupported star stalk is 4.5 mm wide.
- **Assembly service.** Every part is on the front, so assembly is **single-sided SMT**, which avoids the double-sided Standard PCBA requirement. Standard PCBA lists edge rails and fiducials as necessary. Their pages don't say how they handle odd-shaped outlines, so ask JLCPCB support or use their "Panel by JLCPCB" option and look at their panel preview before paying. They recommend 5 mm process edges.
- **Component to board edge.** JLCPCB publishes no minimum for components other than copper to edge (0.2 mm). The nearest LED pad is D4 at 0.77 mm from the edge (D2 0.83, D6 0.89). The USB-C receptacle sits right at the bottom edge by design, so confirm its overhang with JLCPCB's assembly team. Also check that the connector's shell and pads stay clear of the white outline silkscreen.
- **Finish.** Mask over bare copper is not an issue on this board. Exposed ENIG areas are all 1:1 mask openings.
- **Edge.Cuts import.** When you import the outline into KiCad, check that it joins into one closed shape.

## Fab notes
- Matte **black** mask, **white** silkscreen, **ENIG** finish, 1.6 mm FR4. A different board thickness changes the balance.

## Files
- `preview.png` shows the board unlit. `preview_lit.png` shows the star LED (D8) on. `preview_all_lit.png` shows all ten positions lit at once, which the real circuit never does. `preview_pcb_layout.png` shows the placed pads. `preview_stages.png` and `stage_01..10.png` show the 10-stage sequence. `preview_parts_zone.png` overlays the parts zones and USB-C position (blue).
- `source/build_ornament.py` regenerates every layer and prints the balance (Python 3 with shapely and fonttools). It needs the OFL font UnifrakturMaguntia saved as `source/fonts/frak.ttf`.
