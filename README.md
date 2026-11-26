# ScaffVisor — Blender add-on (v0.6.0)

Documentation: **https://raduandrei-source.github.io/ScaffVisor/** (the **Help** button in the panel opens the page for the section you are in).

Systems: 23 built in — frame façade systems (Layher Blitz 70/100, Plettac SL 70/100, Altrad Mostostal Plus, assco quadro, Scafom-rux Framescaff, Hünnebeck BOSTA 70, SLV 70, walk-through frames) and modular systems (ringlock, cuplock, kwikstage, wedge-lock). See `docs/presets.md` and the systems catalog in `docs/catalog/`.

Generates site scaffolding along the walls you mark, with adjustable height, a bill of materials and total weight.

## Changes

### 0.6.0
- 21 new systems, 23 in all. Frame façade: Layher Blitz 70 aluminium and Blitz 100, Plettac SL 70 aluminium and SL 100, Altrad Mostostal Plus 70 / 100, Altrad assco quadro 70, Scafom-rux Framescaff, Hünnebeck BOSTA 70, SLV RAM 2 / SLV 70, A & B walk-through frame. Modular: Coronet, APAC, DSS and PERI UP ringlock / rosette; APAC, DSS and Duscaff cuplock; APAC and Uni-span kwikstage; Waco Wedgelok. Every value comes from a published parts list, with its source; missing parts are flagged as estimated.
- New modular engine: standards (combined per leg up to 1 m above the top deck), base collars, transoms and ledgers per lift, on the same layout and ground following as the frame systems.
- The System list is grouped by grid (systems with the same widths and bay lengths are listed together) and keeps the system of a saved file when systems are added.
- Leg spacing is the nominal system width (axis to axis) for every system.
- Access decks in 1.09-1.10 m frames get the extra 0.32 m deck beside them; jack, guard rail and toeboard lines take the system's own names and flags.
- Layher Blitz 70: the eye bolt weight in the price list is per pack of 10; now 0.18 kg per bolt (estimated).
- Systems catalog (`docs/catalog/`): one sheet per system with a model built by ScaffVisor, dimensioned views, when to use it, parts and sources. The `.blend` models are kept with the project files.

## Licence
GPL-3.0-or-later (see `LICENSE`). One complete product: no key, no account, no online check. Free for teaching and research at universities on request from a university address.

## Install
Blender 4.2 or newer (extension package): drag `scaffvisor-0.6.0.zip` into the Blender window, or Preferences > Get Extensions > top-right menu > Install from Disk.
Update: disable the old version, drag the newer zip, enable. No restart is needed. Remove: Preferences > Add-ons > ScaffVisor > Remove.
The panel is in the 3D Viewport sidebar (N) > **ScaffVisor** tab.

## The panel
**Before a scaffold exists** the panel shows only three things: what will be used as the **Wall** (selected faces, edges, a curve or the base ring of a mesh), the optional **Ground**, and **Generate Scaffold**.

**With a scaffold selected** the top strip shows its name, total weight and the number of notes (click it to read them), plus the **Viewport** options (what to display, Live Update) and Delete. Below are four sections:

| Section | Contents |
|---|---|
| **Layout** | System, height (from faces + offset, or a fixed height), wall offset, side, ends, short bays, path |
| **Ground** | Terrain mesh, slope filter, search height, base pad; *Jacks and Tolerance* folded below |
| **Parts** | Timber grade, toeboards, low decks, cladding |
| **Result** | Quantities, weight per m², notes, parts list (folded), export |

Dimmed lines under a control show its effect (for example the top deck height and number of lifts under Height).
When **Live Update** is off, or the scaffold is very large, a **Rebuild (Out of Date)** button appears at the top. A failed build is shown there too, with its reason.

## Use
**From faces (recommended)**
1. Select the building (or planes you drew on the wall sides), enter Edit Mode and select the wall faces.
2. Click **Generate Scaffold**.
3. The scaffold stands on the side the face normals point to (outside for a normal building). Use **Side › Flip** for courtyards and interiors.
4. Height comes from each face (**Height › From Faces**); **Offset** adds or subtracts a fixed amount.
   Separate walls get separate heights. Faces that touch form one continuous run with corners.
5. **Wall Offset** is the clear distance between the wall and the inner face of the frames (default 0.15 m).

**From a curve or mesh edges**: make a curve (polygon, circle, Bezier) or a mesh the active object, then Generate.
For a mesh in Object Mode the bottom ring is used; in Edit Mode the selected edges. Height then comes from the **Height** field.

Green side arrows show which side of each wall the scaffold is on.

**Export Bill of Materials** writes a CSV (UTF-8, opens correctly in Excel; EU or US number format) into a folder named `<your file>_scaffvisor` next to the .blend.
Every export has a time stamp, so earlier ones are kept. The folder button opens that folder. Unsaved files export to the temporary folder (a warning says so).

## Sloping ground
Set **Ground** to the terrain mesh (a photogrammetry scan that also contains the ruin is fine). Every leg is probed straight down onto it, and
the scaffold is built so that all decks stay horizontal at the heights given by the faces:
- each column gets 2.00 m lifts + a compensation frame (0.5 / 1.0 / 1.5 m, only if needed) + threaded jacks (10-60 cm), so the legs sit on the ground;
- where the ground falls away, columns get extra lifts (a stepped scaffold) and the step ends get end guard rails;
- **Max Slope** ignores steep faces (ruin walls) when probing; **Search Height** is the height above the base of your faces from which the ground is probed.
  Keep it below overhangs and wall tops. If the scan has tall ruin tops near the scaffold, use a cleaned copy of the terrain as Ground;
- tweaks: **Base Pad** (sole boards); under *Jacks and Tolerance*: **Jack Extension** (preferred) and **Top Deck Tolerance** (lets the top deck sit slightly lower to need fewer compensation frames);
- after editing the terrain, press the refresh button next to Ground. The Ground section shows the ground range, jack range and compensation frames; notes list columns that exceed the jack range or cross-slope limits.

## What it does
- Fits bays (1.5 / 2.0 / 2.5 / 3.0 m, optionally 0.74 / 1.10 m) to each wall run.
- Height: 2.00 m lifts + compensation frame (0.5 / 1.0 / 1.5 m) + threaded base jacks (10-60 cm extension).
- Convex and concave corners (~90 deg); gentle corners and curves become a continuous ring.
- Diagonal braces (run ends + every 5th bay), access decks with ladder/hatch, guard rails, toeboards, wall ties (1 per 22 m2, about every 4 m of height).
- Toeboards (15 cm) follow the three-part edge protection of the Plettac system; switch them off in **Parts** if you do not want them (they also leave the bill of materials).
- Low decks: where the ground is high, a deck is also laid on top of the compensation frame, so the wall can be worked from a deck instead of from the ground.
- Hiding rails, braces or ties in the **Viewport** options changes the display only; they stay in the bill of materials.
- Clear walkways: no mid-height or low cross members, decks are flush with their end fittings.
- Bill of materials with weight; parts whose size is not in the catalog are flagged **estimated** (marked * in the parts list).
- Checked against the Plettac catalog example (123 m, 3 lifts): 126 frames, 84 jacks, 27 braces, ~10.7 t (catalog ~10.7 t).

## What it does not do (yet)
- **It is not a stability calculation** and does not replace the manufacturer's manual or an engineer. Ties and braces are indicative.
- Ground is followed with jacks, compensation frames and extra lifts (no stair-stepped bays across a wall, no cross-slope beyond the jack range). Where a system's frame set leaves gaps in the jack range, the notes say which columns are out of range.
- Corners at angles other than ~90 deg are approximate (a note is shown).
- A chain of connected faces with different heights uses its tallest face for the whole chain.
- No brackets/consoles, separate stair towers, passages, roofs or transport planning yet.
