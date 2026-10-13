---
layout: page
title: Systems and presets
---

A scaffold system is a data file in the add-on's `presets` folder. The code contains no dimension or weight of any manufacturer.

## Built in

| System | Status |
|---|---|
| Plettac SL 70 (steel, 74 cm) | Values from the manufacturer's catalog (ed. 04/2013). Checked against its example of 123 m and 3 lifts: 126 frames, 84 jacks, 27 braces, about 10.7 t. Not yet weighed on real parts |
| Layher Blitz 70 (steel, 73 cm) | **Draft.** Frames, decks, access decks, jacks, guard rails and ties from the published price list (guideline weights, "ca."). Diagonals for the 1.57 m bay and short bays are estimated and flagged. Wall-gap and tie rules are still the Plettac placeholders. Not yet checked against a manufacturer example |

More systems are added only from published technical data. Each one lists its sources.

## How values are marked

- **verified**: weighed or measured on the real part. Until then the flag is false, whatever the catalog says. Clones of a system may differ slightly from the original.
- **estimated**: the catalog does not list the part, so the add-on computes it, for example a diagonal for a lift height that has no catalog entry. Estimated weights are flagged in the panel (a star in the parts list) and in the export.
- **sources**: each preset names the documents it came from.

## What a preset contains

- the system: frame width and height, tube diameter, bay lengths, deck width and number of decks per bay, compensation frame heights;
- the components: frames, decks, access decks with ladder and hatch, diagonals, guard rails, toeboards, jacks, ties, with article numbers and weights;
- the rules: ties per area, free height above a tie, braces every few bays, jack extension limits, wall gap limits;
- a sanity check: a catalog example the result is compared against.

## Adding your own

Copy an existing file in `presets/`, change the values, keep the structure, and restart the add-on. It appears in the **System** list. Start from the catalog of your system and fill in the *sources* field.

A friendlier preset manager and CSV import from supplier lists are planned.
